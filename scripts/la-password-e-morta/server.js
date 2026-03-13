/**
 * server.js — WebAuthn Lab (Passkey)
 *
 * Server Express con registrazione e login via passkey.
 * Zero password. ECDSA P-256, Secure Enclave, origin binding.
 *
 * Uso:
 *   npm install
 *   node server.js
 *   Apri http://localhost:3000
 */

const express = require('express');
const session = require('express-session');
const bodyParser = require('body-parser');
const path = require('path');
const crypto = require('crypto');
const {
    generateRegistrationOptions,
    verifyRegistrationResponse,
    generateAuthenticationOptions,
    verifyAuthenticationResponse,
} = require('@simplewebauthn/server');

const app = express();
const PORT = 3000;

// Configurazione
const rpName = 'Signal Pirate Lab';
const rpID = 'localhost';
const origin = `http://localhost:${PORT}`;

// Database in memoria (in produzione: database vero)
const users = new Map();
const pendingChallenges = new Map();

app.use(bodyParser.json());
app.use(session({
    secret: crypto.randomBytes(32).toString('hex'),
    resave: false,
    saveUninitialized: false,
    cookie: { secure: false }, // localhost non ha HTTPS
}));

// Serve il frontend
app.use(express.static(path.join(__dirname, 'public')));

// ============================================================
//  Registrazione
// ============================================================

// POST /register/options — genera le opzioni per navigator.credentials.create()
app.post('/register/options', async (req, res) => {
    const { username } = req.body;
    if (!username) {
        return res.status(400).json({ error: 'username richiesto' });
    }

    // Se l'utente esiste gia', esclude le credenziali esistenti
    const existingUser = users.get(username);
    const excludeCredentials = existingUser
        ? existingUser.credentials.map(c => ({ id: c.id, type: 'public-key' }))
        : [];

    const options = await generateRegistrationOptions({
        rpName,
        rpID,
        userName: username,
        attestationType: 'none',
        excludeCredentials,
        authenticatorSelection: {
            residentKey: 'preferred',
            userVerification: 'preferred',
        },
    });

    // Salva il challenge per la verifica
    pendingChallenges.set(username, {
        challenge: options.challenge,
        type: 'register',
    });

    req.session.username = username;
    res.json(options);
});

// POST /register/verify — verifica la risposta dell'authenticator
app.post('/register/verify', async (req, res) => {
    const username = req.session.username;
    if (!username) {
        return res.status(400).json({ error: 'sessione scaduta' });
    }

    const pending = pendingChallenges.get(username);
    if (!pending || pending.type !== 'register') {
        return res.status(400).json({ error: 'nessun challenge pendente' });
    }

    try {
        const verification = await verifyRegistrationResponse({
            response: req.body,
            expectedChallenge: pending.challenge,
            expectedOrigin: origin,
            expectedRPID: rpID,
            requireUserVerification: false,
        });

        if (verification.verified && verification.registrationInfo) {
            const info = verification.registrationInfo;
            // v10: credentialID (base64url string), credentialPublicKey (Uint8Array), counter
            const credentialId = info.credentialID;
            const publicKey = info.credentialPublicKey;
            const counter = info.counter ?? 0;

            // Crea o aggiorna l'utente
            if (!users.has(username)) {
                users.set(username, { credentials: [] });
            }

            users.get(username).credentials.push({
                id: credentialId,
                publicKey: publicKey,
                counter: counter,
            });

            pendingChallenges.delete(username);

            console.log(`[REGISTER] ${username} — credentialId: ${credentialId}`);
            console.log(`[REGISTER] Chiave pubblica salvata sul server`);
            console.log(`[REGISTER] Chiave privata nel Secure Enclave (mai vista dal server)`);

            res.json({
                verified: true,
                credentialId: credentialId,
            });
        } else {
            res.status(400).json({ error: 'verifica fallita' });
        }
    } catch (err) {
        console.error('[REGISTER ERROR]', err.message);
        res.status(400).json({ error: err.message });
    }
});

// ============================================================
//  Login (Autenticazione)
// ============================================================

// POST /login/options — genera le opzioni per navigator.credentials.get()
app.post('/login/options', async (req, res) => {
    const { username } = req.body;
    if (!username) {
        return res.status(400).json({ error: 'username richiesto' });
    }

    const user = users.get(username);
    if (!user) {
        return res.status(404).json({ error: 'utente non trovato' });
    }

    const options = await generateAuthenticationOptions({
        rpID,
        allowCredentials: user.credentials.map(c => ({
            id: c.id,
            type: 'public-key',
        })),
    });

    pendingChallenges.set(username, {
        challenge: options.challenge,
        type: 'login',
    });

    req.session.username = username;
    res.json(options);
});

// POST /login/verify — verifica la firma ECDSA
app.post('/login/verify', async (req, res) => {
    const username = req.session.username;
    if (!username) {
        return res.status(400).json({ error: 'sessione scaduta' });
    }

    const pending = pendingChallenges.get(username);
    if (!pending || pending.type !== 'login') {
        return res.status(400).json({ error: 'nessun challenge pendente' });
    }

    const user = users.get(username);
    const credentialId = req.body.id;
    const savedCredential = user.credentials.find(c => c.id === credentialId);

    if (!savedCredential) {
        return res.status(400).json({ error: 'credenziale non trovata' });
    }

    try {
        const verification = await verifyAuthenticationResponse({
            response: req.body,
            expectedChallenge: pending.challenge,
            expectedOrigin: origin,
            expectedRPID: rpID,
            requireUserVerification: false,
            authenticator: {
                credentialID: savedCredential.id,
                credentialPublicKey: savedCredential.publicKey,
                counter: savedCredential.counter,
            },
        });

        if (verification.verified) {
            // Aggiorna il contatore (protezione anti-clone)
            const authInfo = verification.authenticationInfo || {};
            savedCredential.counter = authInfo.newCounter ?? authInfo.counter ?? savedCredential.counter + 1;

            pendingChallenges.delete(username);

            console.log(`[LOGIN] ${username} — firma ECDSA verificata`);
            console.log(`[LOGIN] signCount: ${savedCredential.counter}`);
            console.log(`[LOGIN] Zero password coinvolte`);

            res.json({
                verified: true,
                signCount: savedCredential.counter,
            });
        } else {
            res.status(400).json({ error: 'firma non valida' });
        }
    } catch (err) {
        console.error('[LOGIN ERROR]', err.message);
        res.status(400).json({ error: err.message });
    }
});

// ============================================================
//  Info endpoint
// ============================================================
app.get('/info', (req, res) => {
    res.json({
        rpName,
        rpID,
        origin,
        registeredUsers: Array.from(users.keys()),
        totalCredentials: Array.from(users.values())
            .reduce((sum, u) => sum + u.credentials.length, 0),
    });
});

// ============================================================
//  Start
// ============================================================
app.listen(PORT, () => {
    console.log('');
    console.log('='.repeat(50));
    console.log('  WebAuthn Lab — Signal Pirate');
    console.log('='.repeat(50));
    console.log('');
    console.log(`  Server:  http://localhost:${PORT}`);
    console.log(`  rpID:    ${rpID}`);
    console.log(`  Origin:  ${origin}`);
    console.log('');
    console.log('  Registra un username, autentica con Touch ID');
    console.log('  o la security key del browser. Zero password.');
    console.log('');
    console.log('='.repeat(50));
});
