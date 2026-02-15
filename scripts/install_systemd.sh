#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/botvpn"
SERVICE_NAME="botvpn"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

if [[ $EUID -ne 0 ]]; then
  echo "Run as root: sudo bash scripts/install_systemd.sh"
  exit 1
fi

id -u botvpn >/dev/null 2>&1 || useradd --system --create-home --shell /usr/sbin/nologin botvpn
mkdir -p "$APP_DIR"
rsync -a --delete --exclude '.git' --exclude '.venv' ./ "$APP_DIR/"

python3 -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/pip" install --upgrade pip
"$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt"

cp "$APP_DIR/deploy/botvpn.service" "$SERVICE_FILE"
sed -i 's|^User=.*|User=botvpn|' "$SERVICE_FILE"
sed -i 's|^WorkingDirectory=.*|WorkingDirectory=/opt/botvpn|' "$SERVICE_FILE"
sed -i 's|^EnvironmentFile=.*|EnvironmentFile=/opt/botvpn/.env|' "$SERVICE_FILE"
sed -i 's|^ExecStart=.*|ExecStart=/opt/botvpn/.venv/bin/python /opt/botvpn/bot.py|' "$SERVICE_FILE"

chown -R botvpn:botvpn "$APP_DIR"
chmod 600 "$APP_DIR/.env" || true

systemctl daemon-reload
systemctl enable --now "$SERVICE_NAME"
systemctl status "$SERVICE_NAME" --no-pager

echo "Installed. Logs: journalctl -u $SERVICE_NAME -f"
