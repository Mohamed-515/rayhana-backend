# Rayhana Backend

## Email Verification

Rayhana email verification requires real SMTP credentials.

For Gmail:

- Enable 2-Step Verification on the Gmail account.
- Create and use a Gmail App Password.
- Do not use the normal Gmail account password as `SMTP_PASSWORD`.

Development fallback:

- If SMTP is missing or fails while `ENVIRONMENT=development`, the backend keeps the verification code in MongoDB and prints it in the terminal.
- Use the latest printed code to test the Flutter verification flow.

## Flutter Kotlin Cache Recovery

If a Kotlin cache error happens in Flutter, run:

```bash
flutter clean
flutter pub get
flutter run -d c76f33ac
```
