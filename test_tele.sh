#!/bin/bash
TOKEN="8624026555:AAHzsOh95QmuqhoPOYuVhcfl0eifJGH7P54"
CHAT_ID="1537750849"

echo "Running direct script validation payload..."
curl -X POST "https://api.telegram.org/bot${TOKEN}/sendMessage" \
     -d "chat_id=${CHAT_ID}" \
     -d "text=⚡ Executive Hub: Automated script pipeline online."
echo -e "\nDone."
