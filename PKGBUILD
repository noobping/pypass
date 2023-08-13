pkgname=pypass
pkgver=0.1.0
pkgrel=1
pkgdesc="A GTK4 frontend for Password Store"
arch=('any')
url="https://github.com/noobping/pypass"
license=('GPL')
depends=('python' 'gtk4' 'python-gobject' 'pass' 'pass-otp')
makedepends=('sed')
source=(
  'pypass.desktop'
  'pypass.py'
  'pypass.svg'
)
sha256sums=(
  '34025f2e0a828a3ea23ea88fe20e614829b31f6a21ec801fb95a109ec266865a'
  '5982ce67369673f0238402828d005acc00790c951887bd000f0684165287ea10'
  '4f37dfdd3f13dd34183c5397cad60b896c0848624129949ead8508395b229162'
)

package() {
  cd "$srcdir"

  install -Dm755 pypass.py "$pkgdir/usr/bin/pypass"
  install -Dm644 pypass.svg "$pkgdir/usr/share/icons/hicolor/scalable/apps/com.github.noobping.pypass.svg"
  install -Dm644 "$srcdir/pypass.desktop" "$pkgdir/usr/share/applications/com.github.noobping.pypass.desktop"
}
