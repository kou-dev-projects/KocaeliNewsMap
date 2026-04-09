import webpush from "web-push";

const keys = webpush.generateVAPIDKeys();

console.log("Generated VAPID keys for local configuration:");
console.log("");
console.log(`NEXT_PUBLIC_VAPID_PUBLIC_KEY=${keys.publicKey}`);
console.log(`VAPID_PUBLIC_KEY=${keys.publicKey}`);
console.log(`VAPID_PRIVATE_KEY=${keys.privateKey}`);
console.log("VAPID_SUBJECT=mailto:hello@example.com");
