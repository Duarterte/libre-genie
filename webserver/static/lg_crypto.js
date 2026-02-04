/**
 * Generates a UUID v4 and a random 32-byte secret, storing them in localStorage
 * if they do not already exist.
 */
function initIdentity() {
    // Check if UUID already exists
    let uuid = localStorage.getItem('device_uuid');
    if (!uuid) {
        uuid = crypto.randomUUID();
        localStorage.setItem('device_uuid', uuid);
        console.log('Generated and stored new UUID:', uuid);
    }

    // Check if Secret already exists
    let secret = localStorage.getItem('device_secret');
    if (!secret) {
        const randomValues = new Uint8Array(32);
        crypto.getRandomValues(randomValues);
        // Convert Uint8Array to hex string
        secret = Array.from(randomValues)
            .map(b => b.toString(16).padStart(2, '0'))
            .join('');
        localStorage.setItem('device_secret', secret);
        console.log('Generated and stored new Secret');
    }

    return { uuid, secret };
}

async function registerDevice(uuid, secret) {
    try {
        const response = await fetch('/api/register_device', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ client_id: uuid, secret: secret })
        });
        const data = await response.json();
        console.log('Device registered:', data);
    } catch (e) {
        console.error('Failed to register device:', e);
    }
}

async function getUUIDAndSecretCount() {
    const uuid = localStorage.getItem('device_uuid');
    const secret = localStorage.getItem('device_secret');

    if (!uuid || !secret) return;

    try {
        const response = await fetch('/api/uuid_secret_count', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ client_id: uuid, secret: secret })
        });
        const data = await response.json();
        console.log('Credentials status:', data);
        if (data.count === 0) {
            console.log('Device not registered. Registering now...');
            await registerDevice(uuid, secret);
        }
        return data;
    } catch (e) {
        console.error('Failed to check credentials:', e);
    }
}

// Automatically initialize on load and check registration
initIdentity();
getUUIDAndSecretCount();
