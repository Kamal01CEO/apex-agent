/**
 * WhatsApp Live Listener using WhiskeySockets/Baileys
 * Displays terminal QR code for device pairing and syncs incoming messages
 * directly into Apex Agent memory index.
 */

const { default: makeWASocket, useMultiFileAuthState, DisconnectReason } = require('./baileys/lib');
const qrcode = require('qrcode-terminal');
const { exec } = require('child_process');
const path = require('path');

const AUTH_DIR = path.join(__dirname, '../data/wa_auth');

async function connectToWhatsApp() {
  const { state, saveCreds } = await useMultiFileAuthState(AUTH_DIR);

  const sock = makeWASocket({
    auth: state,
    printQRInTerminal: true,
  });

  sock.ev.on('creds.update', saveCreds);

  sock.ev.on('connection.update', (update) => {
    const { connection, lastDisconnect, qr } = update;
    if (qr) {
      console.log('\n📲 Scan this QR code with WhatsApp on your phone to link Apex Agent:');
      qrcode.generate(qr, { small: true });
    }
    if (connection === 'close') {
      const shouldReconnect = (lastDisconnect?.error)?.output?.statusCode !== DisconnectReason.loggedOut;
      console.log('WhatsApp connection closed due to ', lastDisconnect?.error, ', reconnecting: ', shouldReconnect);
      if (shouldReconnect) {
        connectToWhatsApp();
      }
    } else if (connection === 'open') {
      console.log('✅ WhatsApp successfully connected to Apex Agent!');
    }
  });

  sock.ev.on('messages.upsert', async (m) => {
    const msg = m.messages[0];
    if (!msg.key.fromMe && m.type === 'notify') {
      const sender = msg.pushName || msg.key.remoteJid.split('@')[0];
      const text = msg.message?.conversation || msg.message?.extendedTextMessage?.text || '';

      if (text) {
        console.log(`\n📩 Received WhatsApp from [${sender}]: "${text}"`);
        console.log('⚡ Autonomously saving to Apex Agent memory index...');

        // Execute apex CLI auto_save_memory
        const apexBin = path.join(__dirname, '../.venv/bin/apex');
        const cmd = `"${apexBin}" run-goal "Save this WhatsApp conversation from ${sender}: ${text.replace(/"/g, '\\"')}"`;
        exec(cmd, (err, stdout) => {
          if (err) console.error('Error saving to memory:', err);
          else console.log('✔ Saved to Apex Agent memory.');
        });
      }
    }
  });
}

connectToWhatsApp();
