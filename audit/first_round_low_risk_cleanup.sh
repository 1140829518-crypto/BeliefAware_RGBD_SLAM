#!/usr/bin/env bash
set -u

WIN_USER="/mnt/c/Users/de'l'l"
LOG="/tmp/first_round_low_risk_cleanup.log"
KEEP_WSL_COMMIT="110a328ea54b42367b803ec53ee0bf52ef26b419"
: > "$LOG"

log() { printf '%s\n' "$*" | tee -a "$LOG"; }
size() { du -sh "$1" 2>/dev/null | awk '{print $1}' || printf '0'; }

clear_contents() {
    local target="$1"
    if [ ! -d "$target" ]; then
        log "SKIP missing: $target"
        return 0
    fi
    log "CLEAR contents: $target (before=$(size "$target"))"
    # Locked/in-use files are deliberately retained; failures do not trigger forceful handling.
    find "$target" -mindepth 1 -depth -delete 2>>"$LOG" || true
    log "AFTER: $target ($(size "$target"))"
}

log "=== BEFORE ==="
df -h /mnt/c / 2>>"$LOG" | tee -a "$LOG"

# 1. NVIDIA shader cache.
clear_contents "$WIN_USER/AppData/Local/NVIDIA/DXCache"

# 2. WSL pip cache, using pip's supported cache command.
log "PURGE WSL pip cache: /home/djn/.cache/pip (before=$(size /home/djn/.cache/pip))"
python3 -m pip cache purge >>"$LOG" 2>&1 || true
log "AFTER WSL pip cache: $(size /home/djn/.cache/pip)"

# 3. Windows Conda cache: archive/index cache only. Never touch pkgs directories or envs.
CONDA_PKGS="$WIN_USER/.conda/pkgs"
log "PURGE Windows Conda archives/index only: $CONDA_PKGS"
if [ -d "$CONDA_PKGS" ]; then
    find "$CONDA_PKGS" -maxdepth 1 -type f \( -name '*.conda' -o -name '*.tar.bz2' -o -name '*.part' \) -delete 2>>"$LOG" || true
    clear_contents "$CONDA_PKGS/cache"
fi

# 4. Current user's Windows temporary directory. Locked files are skipped.
clear_contents "$WIN_USER/AppData/Local/Temp"

# 5. Browser caches only; profiles, cookies, history, passwords and bookmarks remain untouched.
for browser_root in \
    "$WIN_USER/AppData/Local/Google/Chrome/User Data" \
    "$WIN_USER/AppData/Local/Microsoft/Edge/User Data"
do
    [ -d "$browser_root" ] || continue
    while IFS= read -r -d '' cache_dir; do
        case "$cache_dir" in
            "$browser_root"/*) clear_contents "$cache_dir" ;;
        esac
    done < <(find "$browser_root" -type d \( \
        -name 'Cache' -o -name 'Code Cache' -o -name 'GPUCache' -o \
        -name 'DawnCache' -o -name 'ShaderCache' -o -name 'GrShaderCache' -o \
        -name 'CacheStorage' \) -print0 2>>"$LOG")
done

# 6. Current user's recycle bin only.
clear_contents "/mnt/c/\$Recycle.Bin/S-1-5-21-210478259-981595955-2673639994-1001"

# 7. VS Code extension installation caches only, never installed extensions.
clear_contents "$WIN_USER/AppData/Roaming/Code/CachedExtensionVSIXs"
clear_contents "/home/djn/.vscode-server/data/CachedExtensionVSIXs"

# 8. Old VS Code Remote WSL download versions; retain the commit currently installed in WSL.
REMOTE_ROOT="$WIN_USER/vscode-remote-wsl/stable"
if [ -d "$REMOTE_ROOT" ]; then
    for version_dir in "$REMOTE_ROOT"/*; do
        [ -d "$version_dir" ] || continue
        version="$(basename "$version_dir")"
        if [ "$version" = "$KEEP_WSL_COMMIT" ]; then
            log "KEEP current VS Code WSL download: $version_dir"
        else
            clear_contents "$version_dir"
            rmdir "$version_dir" 2>>"$LOG" || true
        fi
    done
fi

# 9. Windows pip cache only. Windows interop is unavailable, so purge the documented cache directory.
clear_contents "$WIN_USER/AppData/Local/pip/cache"

# 10. NVIDIA installer download cache only.
clear_contents "/mnt/c/ProgramData/NVIDIA Corporation/Downloader"

# 11. Supported journal vacuum operation; preserve recent logs and cap retained journal size.
log "VACUUM journal: retain <=14 days and <=300M"
if sudo -n true 2>/dev/null; then
    sudo -n journalctl --vacuum-time=14d --vacuum-size=300M >>"$LOG" 2>&1 || true
else
    journalctl --vacuum-time=14d --vacuum-size=300M >>"$LOG" 2>&1 || true
fi

# 12. Windows crash dumps only.
clear_contents "$WIN_USER/AppData/Local/CrashDumps"

log "=== AFTER ==="
df -h /mnt/c / 2>>"$LOG" | tee -a "$LOG"
stat -c 'ext4.vhdx_bytes=%s path=%n' "$WIN_USER/AppData/Local/Packages/CanonicalGroupLimited.Ubuntu20.04LTS_79rhkp1fndgsc/LocalState/ext4.vhdx" 2>>"$LOG" | tee -a "$LOG"
du -sh /home/djn /home/djn/.cache /home/djn/.vscode-server /var/log /var/cache/apt 2>/dev/null | sort -hr | tee -a "$LOG"
log "LOG=$LOG"
