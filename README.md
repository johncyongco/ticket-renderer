# Deploy the UN/FOLD ticket renderer

The renderer takes an attendee name and ticket code from n8n and returns a PNG with the UN/FOLD header and a matching QR code. n8n generates and saves the code, sends the PNG by Gmail, and records the send status in Google Sheets.

## 1. Build and start the renderer

Run these commands on the Docker host running n8n. Open the project folder containing `Dockerfile`, `renderer.py`, and `header.png`.

```powershell
docker ps --format "{{.Names}}"
docker network create unfold-net
docker network connect unfold-net YOUR_N8N_CONTAINER
docker build -t unfold-ticket-renderer .
docker run -d --restart unless-stopped --name unfold-ticket-renderer --network unfold-net unfold-ticket-renderer
```

Replace `YOUR_N8N_CONTAINER` with the actual container name. If you already have a user-defined Docker network for n8n, you can reuse its name and skip creating and connecting the network. If n8n is managed by Docker Compose and gets recreated, declare the shared network in its Compose configuration so the new container reconnects.

## 2. Configure n8n

1. Open **Render PNG ticket** and use `POST http://unfold-ticket-renderer:8080/ticket`.
2. Keep the imported node's JSON body mapping for the attendee name and ticket code. The response format is **File** and the output field is `ticket`.
3. Connect the Google Sheets and Gmail credentials. Use the same registration tab in all four Sheets nodes. In **Prepare ticket**, match the name and email headers to your spreadsheet.
4. Add these column headers if missing: `Payment Status`, `Ticket Code`, `Ticket Status`, and `Ticket Sent At`.

## 3. Verify before turning on the schedule

Use a copy of the response tab with one registration addressed to your own email. Set **Payment Status** to `Paid`, leave **Ticket Status** blank, and run **Manual test**. The row should get a ticket code, the email should include a PNG, and scanning the QR should return that same code. After the email sends, the row should show `Sent`.

Run only one issuance execution at a time. The workflow uses Google Sheets row updates to track sending. If a row stays at `Sending`, search Gmail Sent for its code before retrying. Set it to `Pending` only after confirming it needs to be sent, and keep its existing code.

If the renderer is unreachable, run `docker network inspect unfold-net` and confirm both containers appear. Use `docker logs unfold-ticket-renderer` to check whether the request arrived.
