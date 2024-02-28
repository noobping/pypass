FROM alpine:latest
RUN apk add --no-cache libc6-compat file fuse appstream squashfs-tools

RUN curl -L $(curl -L "https://api.github.com/repos/AppImage/AppImageKit/releases/latest" | jq -r '.assets[] | select(.name | test("appimagetool-x86_64.AppImage$")) | .browser_download_url') -o /usr/bin/appimagetool.AppImage \
    && chmod +x appimagetool.AppImage

COPY pypass.py pypass.py
COPY pypass.svg pypass.svg
COPY pypass.desktop pypass.desktop

RUN mkdir -p airrootfs/etc/apk \
    && cp -R /etc/apk airrootfs/etc/ \
    && apk add --no-cache --initdb --root /home/nick/airrootfs pass pass-otp python3 gtk4.0 py3-gobject3 libnotify \
    && rm -fr airrootfs/var/cache \
    && rm -fr airrootfs/*/apk

RUN install -Dm755 pypass.py "airrootfs/usr/bin/pypass" \
    && install -Dm644 pypass.svg "airrootfs/usr/share/icons/hicolor/scalable/apps/com.github.noobping.pypass.svg" \
    && install -Dm644 pypass.desktop "airrootfs/usr/share/applications/com.github.noobping.pypass.desktop" \
    && ( cd airrootfs/ && ln -s usr/share/applications/com.github.noobping.pypass.desktop pypass.desktop && ln -s usr/share/icons/hicolor/scalable/apps/com.github.noobping.pypass.svg com.github.noobping.pypass.svg )

VOLUME /data
WORKDIR /data
RUN appimagetool.AppImage airrootfs
