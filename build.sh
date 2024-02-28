#!/bin/sh
if ! command -v appimagetool.AppImage >/dev/null 2>&1
then
    echo "Download AppImage tool..."
    LATEST_TOOL=$(curl -L "https://api.github.com/repos/AppImage/AppImageKit/releases/latest" | jq -r '.assets[] | select(.name | test("appimagetool-x86_64.AppImage$")) | .browser_download_url')
    curl -L $LATEST_TOOL -o appimagetool.AppImage
    chmod +x appimagetool.AppImage

    doas apk add libc6-compat file fuse appstream squashfs-tools
fi

echo "Build airrootfs..."
mkdir -p airrootfs/etc/apk
cp -R /etc/apk airrootfs/etc/
doas apk add --no-cache --initdb --root /home/nick/airrootfs pass pass-otp python3 gtk4.0 py3-gobject3
doas rm -fr airrootfs/var/cache
doas rm -fr airrootfs/*/apk

echo "Install pypass..."
install -Dm755 pypass.py "airrootfs/usr/bin/pypass"
install -Dm644 pypass.svg "airrootfs/usr/share/icons/hicolor/scalable/apps/com.github.noobping.pypass.svg"
install -Dm644 pypass.desktop "airrootfs/usr/share/applications/com.github.noobping.pypass.desktop"

ln -s usr/share/applications/com.github.noobping.pypass.desktop pypass.desktop
ln -s usr/share/icons/hicolor/scalable/apps/com.github.noobping.pypass.svg com.github.noobping.pypass.svg

python3 -m venv airrootfs/venv
( source airrootfs/venv/bin/activate && pip install PyGObject )

echo "Build AppImage..."
if command -v appimagetool.AppImage >/dev/null 2>&1
then appimagetool.AppImage airrootfs
else
    ./appimagetool.AppImage airrootfs
fi
