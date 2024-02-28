# Contributor: noobping <hello@noobping.dev>
# Maintainer: noobping <hello@noobping.dev>
pkgname=pypass
pkgver=0.0.1
pkgrel=1
pkgdesc="A GTK4 frontend for Password Store written in python"
url="https://github.com/noobping/pypass"
arch="all"
license="GPL"
depends="python3 gtk4.0 py3-gobject3 libnotify"
source="pypass.desktop pypass.py pypass.svg"
builddir="$srcdir/"

package() {
	cd "$srcdir/"

	install -Dm755 pypass.py "$pkgdir/usr/bin/pypass"
	install -Dm644 pypass.svg "$pkgdir/usr/share/icons/hicolor/scalable/apps/com.github.noobping.pypass.svg"
	install -Dm644 pypass.desktop "$pkgdir/usr/share/applications/com.github.noobping.pypass.desktop"
}

sha512sums="
001f2895972184faba68747fa1d0bc69e8b48e768d6b4c31f18db6df6d339294ad54be5e73032ce9fa1695f5669106e41f6ac95009b84013dbdc81db62f6e4f9  pypass.desktop
f52caa0569627b0b54770dec4908d50d34ba5ced09f695b35f65b58c661cd6b4a6a4d9da3b3c57a9d407b10c5b9772012b8e45c836a866a72e44ccae59325e78  pypass.py
4db816c7e7a2e9a76a7e88798c191ec433f89b9b9f733d1b65f4ecf118e9a5db48d4db4b440fa0eb78e70912fea2da8da50a3226d0028bc12d410f3b828d0ddb  pypass.svg
"
