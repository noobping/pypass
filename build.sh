#!/bin/sh
mkdir -p AppDir/usr/share/icons/hicolor/scalable/apps AppDir/usr/bin AppDir/usr/share/applications
install -Dm755 pypass.py "AppDir/usr/bin/pypass"
install -Dm644 pypass.svg "AppDir/usr/share/icons/hicolor/scalable/apps/com.github.noobping.pypass.svg"
install -Dm644 pypass.desktop "AppDir/usr/share/applications/com.github.noobping.pypass.desktop"

if ! command -v appimagetool.AppImage >/dev/null 2>&1
then
    echo "Download AppImage tool..."
    LATEST_TOOL=$(curl -L "https://api.github.com/repos/AppImage/AppImageKit/releases/latest" | jq -r '.assets[] | select(.name | test("appimagetool-x86_64.AppImage$")) | .browser_download_url')
    curl -L $LATEST_TOOL -o appimagetool.AppImage
    chmod +x appimagetool.AppImage
fi

echo "Build AppImage..."
if command -v appimagetool.AppImage >/dev/null 2>&1
then ARCH=x86_64 appimagetool.AppImage -v AppDir
else
    ARCH=x86_64 ./appimagetool.AppImage --appimage-extract-and-run -v AppDir
    rm ./appimagetool.AppImage
fi
