pkgname=gpass
pkgver=0.1.0
pkgrel=1
pkgdesc="A GTK4 frontend for Password Store"
arch=('any')
url="https://github.com/noobping/gpass"
license=('GPL')
depends=('python' 'gtk4' 'python-gobject' 'pass' 'pass-otp')
makedepends=('sed')
source=(
  'gpass.desktop'
  'gpass.py'
  'gpass.svg'
)
sha256sums=(
  '1b87436e3990123d85374ad92a65b1ffba97f7b2219c6049202b1533953eaf4b'
  '19fad93db503b36094a24dfee1b91cd65aaec1aad2b9859229806c2943d97b64'
  '3f530ac74af9e53e14af5168f004ed46cd0f1ad16babccbd21dc7f6f3c723471'
)

package() {
  cd "$srcdir"

  install -Dm755 gpass.py "$pkgdir/usr/bin/gpass"
  install -Dm644 gpass.svg "$pkgdir/usr/share/icons/hicolor/scalable/apps/com.github.noobping.gpass.svg"
  install -Dm644 "$srcdir/gpass.desktop" "$pkgdir/usr/share/applications/com.github.noobping.gpass.desktop"
}
