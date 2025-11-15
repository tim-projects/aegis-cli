# Maintainer: Your Name <your@email.com>
pkgname=aegis-cli
pkgver=0.1.0
pkgrel=1
pkgdesc="A command-line interface (CLI) tool for viewing Aegis Authenticator TOTP codes."
arch=('x86_64') # Adjust if you need other architectures
url="https://github.com/tim-projects/${pkgname}"
license=('GPL3')
depends=()
makedepends=('go')

source=("${pkgname}-${pkgver}.tar.gz::https://github.com/tim-projects/${pkgname}/archive/v${pkgver}.tar.gz")
sha256sums=('SKIP') # IMPORTANT: Replace 'SKIP' with the actual checksum of the release tarball before AUR submission.

build() {
  cd "${srcdir}/${pkgname}-${pkgver}"
  go mod tidy
  go build -o "${pkgname}" ./cmd/aegis-cli/main.go
}

package() {
  install -d "${pkgdir}/usr/bin"
  install -m 755 "${srcdir}/${pkgname}-${pkgver}/${pkgname}" "${pkgdir}/usr/bin/"

  install -d "${pkgdir}/usr/share/licenses/${pkgname}"
  install -m 644 "${srcdir}/${pkgname}-${pkgver}/LICENSE" "${pkgdir}/usr/share/licenses/${pkgname}/"
}
