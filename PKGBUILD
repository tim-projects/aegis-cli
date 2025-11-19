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

build() {
  # Change into the source directory where go.mod is located.
  # This is necessary when BUILDDIR is set externally (e.g., /tmp/makepkg).
  cd "${srcdir}" 

  # Set Go-specific variables to use the source directory
  export GOCACHE="${srcdir}/.go_cache"
  export GOMODCACHE="${srcdir}/.go_mod_cache"
  export GOPATH="${srcdir}/.go"
  
  go mod tidy -v
  go build -v -modcacherw -o "${srcdir}/${pkgname}" github.com/tim-projects/aegis-cli/cmd/aegis-cli
}

package() {
  install -d "${pkgdir}/usr/bin"
  install -m 755 "${srcdir}/${pkgname}" "${pkgdir}/usr/bin/"

  install -d "${pkgdir}/usr/share/licenses/${pkgname}"
  install -m 644 "${srcdir}/LICENSE" "${pkgdir}/usr/share/licenses/${pkgname}/"
}
