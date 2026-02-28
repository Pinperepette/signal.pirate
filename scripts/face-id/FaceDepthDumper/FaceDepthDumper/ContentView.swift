import SwiftUI
import ARKit
import RealityKit

struct ContentView: View {
    @StateObject private var arModel = ARModel()

    var body: some View {
        ZStack {
            ARViewContainer(arModel: arModel)
                .edgesIgnoringSafeArea(.all)

            VStack {
                Spacer()

                if let depthImage = arModel.depthImage {
                    Image(uiImage: depthImage)
                        .resizable()
                        .scaledToFit()
                        .frame(height: 200)
                        .border(Color.green, width: 2)
                        .padding(.bottom, 8)
                }

                HStack(spacing: 20) {
                    Button(action: { arModel.saveDepthMap() }) {
                        Label("Salva Depth", systemImage: "square.and.arrow.down")
                            .padding()
                            .background(Color.green)
                            .foregroundColor(.black)
                            .cornerRadius(10)
                    }

                    Button(action: { arModel.savePhoto() }) {
                        Label("Salva Foto", systemImage: "camera")
                            .padding()
                            .background(Color.blue)
                            .foregroundColor(.white)
                            .cornerRadius(10)
                    }
                }
                .padding(.bottom, 40)

                Text(arModel.statusText)
                    .font(.system(.caption, design: .monospaced))
                    .foregroundColor(.green)
                    .padding(.bottom, 20)
            }
        }
    }
}

struct ARViewContainer: UIViewRepresentable {
    let arModel: ARModel

    func makeUIView(context: Context) -> ARView {
        let arView = ARView(frame: .zero)

        let config = ARFaceTrackingConfiguration()
        config.isWorldTrackingEnabled = false

        arView.session.delegate = arModel
        arView.session.run(config)

        arModel.arView = arView

        return arView
    }

    func updateUIView(_ uiView: ARView, context: Context) {}
}

class ARModel: NSObject, ObservableObject, ARSessionDelegate {
    @Published var depthImage: UIImage?
    @Published var statusText: String = "In attesa del volto..."

    var arView: ARView?
    private var frameCount = 0

    func session(_ session: ARSession, didUpdate frame: ARFrame) {
        guard let faceAnchor = frame.anchors.compactMap({ $0 as? ARFaceAnchor }).first else { return }

        frameCount += 1

        // Aggiorna depth map ogni 10 frame
        if frameCount % 10 == 0 {
            // Depth dalla TrueDepth camera
            if let depthData = frame.capturedDepthData {
                let depthMap = depthData.depthDataMap
                let ciImage = CIImage(cvPixelBuffer: depthMap)
                let context = CIContext()
                if let cgImage = context.createCGImage(ciImage, from: ciImage.extent) {
                    DispatchQueue.main.async {
                        self.depthImage = UIImage(cgImage: cgImage)
                    }
                }
            }

            // Estrai dati dal face anchor
            let vertices = faceAnchor.geometry.vertices
            let transform = faceAnchor.transform

            let pos = transform.columns.3
            let blendShapes = faceAnchor.blendShapes

            let mouthOpen = blendShapes[.jawOpen]?.floatValue ?? 0
            let eyeBlinkL = blendShapes[.eyeBlinkLeft]?.floatValue ?? 0
            let eyeBlinkR = blendShapes[.eyeBlinkRight]?.floatValue ?? 0

            DispatchQueue.main.async {
                self.statusText = """
                Vertici mesh: \(vertices.count)
                Posizione: (\(String(format: "%.3f", pos.x)), \(String(format: "%.3f", pos.y)), \(String(format: "%.3f", pos.z)))
                Bocca: \(String(format: "%.2f", mouthOpen)) | Occhi: L\(String(format: "%.2f", eyeBlinkL)) R\(String(format: "%.2f", eyeBlinkR))
                Frame: \(self.frameCount)
                """
            }
        }
    }

    func saveDepthMap() {
        guard let arView = arView,
              let frame = arView.session.currentFrame else {
            updateStatus("Nessun frame disponibile")
            return
        }

        // Salva la mesh 3D del volto
        if let faceAnchor = frame.anchors.compactMap({ $0 as? ARFaceAnchor }).first {
            saveFaceMesh(faceAnchor)
        }

        // Salva depth map come immagine
        if let depthData = frame.capturedDepthData {
            let depthMap = depthData.depthDataMap
            let ciImage = CIImage(cvPixelBuffer: depthMap)
            let context = CIContext()
            if let cgImage = context.createCGImage(ciImage, from: ciImage.extent) {
                let uiImage = UIImage(cgImage: cgImage)
                UIImageWriteToSavedPhotosAlbum(uiImage, nil, nil, nil)
                updateStatus("Depth map salvata nel rullino")
            }
        } else {
            updateStatus("Depth map non disponibile - salvo solo mesh")
        }
    }

    func savePhoto() {
        guard let arView = arView,
              let frame = arView.session.currentFrame else {
            updateStatus("Nessun frame disponibile")
            return
        }

        let ciImage = CIImage(cvPixelBuffer: frame.capturedImage)
        let context = CIContext()
        if let cgImage = context.createCGImage(ciImage, from: ciImage.extent) {
            let uiImage = UIImage(cgImage: cgImage)
            UIImageWriteToSavedPhotosAlbum(uiImage, nil, nil, nil)
            updateStatus("Foto IR salvata nel rullino")
        }
    }

    private func saveFaceMesh(_ anchor: ARFaceAnchor) {
        let vertices = anchor.geometry.vertices
        let triangles = anchor.geometry.triangleIndices

        // Esporta come OBJ
        var obj = "# Face mesh - \(vertices.count) vertici\n"
        for v in vertices {
            obj += "v \(v.x) \(v.y) \(v.z)\n"
        }
        for i in stride(from: 0, to: triangles.count, by: 3) {
            let a = Int(triangles[i]) + 1
            let b = Int(triangles[i + 1]) + 1
            let c = Int(triangles[i + 2]) + 1
            obj += "f \(a) \(b) \(c)\n"
        }

        // Salva nel Documents
        if let docs = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first {
            let url = docs.appendingPathComponent("face_mesh.obj")
            try? obj.write(to: url, atomically: true, encoding: .utf8)
            updateStatus("Mesh salvata: \(vertices.count) vertici, \(triangles.count / 3) triangoli → face_mesh.obj")
        }
    }

    private func updateStatus(_ text: String) {
        DispatchQueue.main.async {
            self.statusText = text
        }
    }
}
