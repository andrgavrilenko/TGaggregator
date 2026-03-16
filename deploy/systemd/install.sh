#!/usr/bin/env bash
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "Run as root"
  exit 1
fi

cp deploy/systemd/tgaggerator-api.service /etc/systemd/system/
cp deploy/systemd/tgaggerator-collector.service /etc/systemd/system/
cp deploy/systemd/tgaggerator-ui.service /etc/systemd/system/
cp deploy/systemd/tgaggerator-telegram-ui.service /etc/systemd/system/

systemctl daemon-reload
systemctl enable tgaggerator-api.service
systemctl enable tgaggerator-collector.service
systemctl enable tgaggerator-ui.service
systemctl enable tgaggerator-telegram-ui.service

echo "Installed. Start with:"
echo "  systemctl start tgaggerator-api"
echo "  systemctl start tgaggerator-collector"
echo "  systemctl start tgaggerator-ui"
echo "  systemctl start tgaggerator-telegram-ui"
