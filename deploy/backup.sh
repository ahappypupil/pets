#!/usr/bin/env bash
# 每日备份 pets 库，保留 30 天。放到 /opt/pets/deploy/backup.sh，chmod +x
# crontab -e 添加：0 3 * * * /opt/pets/deploy/backup.sh >> /var/log/pets/backup.log 2>&1
set -euo pipefail

set -a
source /opt/pets/.env
set +a

BACKUP_DIR=/var/backups/pets
mkdir -p "$BACKUP_DIR"
STAMP=$(date +%Y%m%d_%H%M%S)
OUT="$BACKUP_DIR/pets_$STAMP.sql.gz"

# 注：应用账号只有 pets.* 权限，去掉 --routines 避免权限不足报错
mysqldump -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -p"$DB_PASSWORD" \
    --single-transaction --default-character-set=utf8mb4 "$DB_NAME" \
    | gzip > "$OUT"

chmod 600 "$OUT"

# 保留最近 30 份
ls -1t "$BACKUP_DIR"/pets_*.sql.gz | tail -n +31 | xargs -r rm -f

echo "[$(date)] backup ok: $OUT ($(du -h "$OUT" | cut -f1))"
