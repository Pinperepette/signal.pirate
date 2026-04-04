// graveyard-scanner.js
// Lancia con: node graveyard-scanner.js [percorso/node_modules]

const fs = require('fs');
const path = require('path');

const nmDir = process.argv[2] || './node_modules';
const suspects = [];
const LIFECYCLE = ['preinstall', 'postinstall', 'install', 'prepare'];
const DANGER = [
    { pat: /\beval\s*\(/, label: 'eval()' },
    { pat: /\bFunction\s*\(/, label: 'Function()' },
    { pat: /child_process/, label: 'child_process' },
    { pat: /\bexec\s*\(/, label: 'exec()' },
    { pat: /\bexecSync\s*\(/, label: 'execSync()' },
    { pat: /process\.env/, label: 'process.env' },
    { pat: /\.ssh\//, label: '.ssh/ access' },
    { pat: /\.bash_history|\.zsh_history/, label: 'shell history' },
    { pat: /curl\s.*\|\s*bash/, label: 'curl | bash' },
    { pat: /Invoke-WebRequest/, label: 'PowerShell download' },
];

function scanPackage(pkgDir) {
    const pkgFile = path.join(pkgDir, 'package.json');
    if (!fs.existsSync(pkgFile)) return;
    let pkg;
    try {
        pkg = JSON.parse(fs.readFileSync(pkgFile, 'utf8'));
    } catch(e) { return; }
    const findings = [];

    // Check lifecycle scripts
    if (pkg.scripts) {
        LIFECYCLE.forEach(hook => {
            if (pkg.scripts[hook]) {
                findings.push(`\x1b[31mLIFECYCLE\x1b[0m ${hook} = "${pkg.scripts[hook]}"`);
            }
        });
    }

    // Scan JS files per pattern sospetti
    const jsFiles = getJsFiles(pkgDir, 2);
    jsFiles.forEach(file => {
        try {
            const src = fs.readFileSync(file, 'utf8');
            DANGER.forEach(({ pat, label }) => {
                if (pat.test(src)) {
                    const rel = path.relative(pkgDir, file);
                    findings.push(`\x1b[33mPATTERN\x1b[0m  ${label} in ${rel}`);
                }
            });
        } catch(e) {}
    });

    if (findings.length > 0) {
        suspects.push({ name: pkg.name, version: pkg.version, findings });
    }
}

function getJsFiles(dir, depth) {
    if (depth < 0) return [];
    let results = [];
    try {
        fs.readdirSync(dir).forEach(f => {
            const full = path.join(dir, f);
            try {
                const stat = fs.statSync(full);
                if (stat.isDirectory() && f !== 'node_modules' && !f.startsWith('.')) {
                    results = results.concat(getJsFiles(full, depth - 1));
                } else if (f.endsWith('.js') && stat.size < 500000) {
                    results.push(full);
                }
            } catch(e) {}
        });
    } catch(e) {}
    return results;
}

// Check che node_modules esista
if (!fs.existsSync(nmDir)) {
    console.log(`\n\x1b[31mErrore:\x1b[0m ${nmDir} non trovato.`);
    console.log('Uso: node graveyard-scanner.js /percorso/node_modules\n');
    process.exit(1);
}

// Scan
console.log(`\n\x1b[32m=== GRAVEYARD SCANNER ===\x1b[0m`);
console.log(`Scansione cimitero: ${path.resolve(nmDir)}\n`);

let total = 0;
fs.readdirSync(nmDir).forEach(entry => {
    const full = path.join(nmDir, entry);
    try {
        if (entry.startsWith('@') && fs.statSync(full).isDirectory()) {
            fs.readdirSync(full).forEach(sub => {
                scanPackage(path.join(full, sub));
                total++;
            });
        } else if (fs.statSync(full).isDirectory()) {
            scanPackage(full);
            total++;
        }
    } catch(e) {}
});

// Report
console.log(`Pacchetti scansionati: ${total}`);
console.log(`Sospetti: \x1b[31m${suspects.length}\x1b[0m\n`);

suspects.forEach(s => {
    console.log(`\x1b[31m[!]\x1b[0m ${s.name}@${s.version}`);
    s.findings.forEach(f => console.log(`    ${f}`));
    console.log();
});

if (suspects.length === 0) {
    console.log('\x1b[32mNessun pattern sospetto trovato.\x1b[0m');
    console.log('(non significa che sia sicuro, significa che lo scanner non ha trovato nulla)\n');
} else {
    console.log(`\x1b[33mAttenzione:\x1b[0m molti di questi sono falsi positivi (moduli nativi, tool legittimi).`);
    console.log(`Ma quanti di questi pacchetti avete letto davvero?\n`);
}
