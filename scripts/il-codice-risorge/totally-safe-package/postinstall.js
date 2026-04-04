// postinstall.js
// Questo e' quello che QUALSIASI pacchetto npm puo' fare
// quando fate npm install. Senza permessi extra. Senza root.

const fs = require('fs');
const os = require('os');
const home = os.homedir();

console.log('\n\x1b[31m=== TOTALLY SAFE PACKAGE ===\x1b[0m');
console.log('Ciao! Sono un postinstall script.');
console.log('Ecco cosa posso leggere:\n');

// 1. Le tue variabili d'ambiente (token, credenziali, API key)
const interessanti = Object.keys(process.env)
    .filter(k => /token|key|secret|pass|auth|api|credential/i.test(k));
console.log(`\x1b[33m[ENV]\x1b[0m Variabili sensibili trovate: ${interessanti.length}`);
interessanti.forEach(k => {
    const val = process.env[k];
    const masked = val.length > 4 ? val.slice(0, 4) + '****' : '****';
    console.log(`  ${k} = ${masked}`);
});
if (interessanti.length === 0) {
    console.log('  (nessuna trovata con pattern token/key/secret/pass/auth/api)');
}

// 2. Le tue chiavi SSH
const sshDir = `${home}/.ssh`;
try {
    const keys = fs.readdirSync(sshDir);
    console.log(`\n\x1b[33m[SSH]\x1b[0m File in ~/.ssh:`);
    keys.forEach(k => {
        const stat = fs.statSync(`${sshDir}/${k}`);
        console.log(`  ${k} (${stat.size} bytes)`);
    });
} catch(e) {
    console.log('\n\x1b[32m[SSH]\x1b[0m Nessuna cartella .ssh trovata');
}

// 3. La tua history (comandi, password digitate per sbaglio)
const histFiles = ['.bash_history', '.zsh_history'];
histFiles.forEach(f => {
    try {
        const hist = fs.readFileSync(`${home}/${f}`, 'utf8');
        const lines = hist.split('\n').filter(Boolean);
        console.log(`\n\x1b[33m[HISTORY]\x1b[0m ${f}: ${lines.length} comandi. Ultimi 5:`);
        lines.slice(-5).forEach(l => console.log(`  > ${l}`));
    } catch(e) {}
});

// 4. File di configurazione (AWS, GCP, Azure, Docker, K8s, npm)
const configs = [
    '.aws/credentials',
    '.aws/config',
    '.npmrc',
    '.docker/config.json',
    '.kube/config',
    '.gitconfig',
    '.netrc',
    '.gnupg/pubring.kbx',
    '.config/gcloud/credentials.db',
];
console.log(`\n\x1b[33m[CONFIG]\x1b[0m File di configurazione accessibili:`);
let foundConfigs = 0;
configs.forEach(c => {
    const full = `${home}/${c}`;
    if (fs.existsSync(full)) {
        try {
            const stat = fs.statSync(full);
            console.log(`  ~/${c} \x1b[31mTROVATO\x1b[0m (${stat.size} bytes, leggibile)`);
            foundConfigs++;
        } catch(e) {}
    }
});
if (foundConfigs === 0) {
    console.log('  (nessun file di configurazione sensibile trovato)');
}

// 5. Info sistema
console.log(`\n\x1b[33m[SYSTEM]\x1b[0m`);
console.log(`  Utente: ${os.userInfo().username}`);
console.log(`  Home: ${home}`);
console.log(`  OS: ${os.type()} ${os.release()}`);
console.log(`  Hostname: ${os.hostname()}`);
console.log(`  CWD: ${process.cwd()}`);

console.log('\n\x1b[32m=== FINE ===\x1b[0m');
console.log('Non ho mandato niente da nessuna parte.');
console.log('Ma un pacchetto malevolo lo avrebbe fatto.');
console.log('Tutto questo, con un semplice npm install.\n');
