Name:           mochi-companion
Version:        1.0.0
Release:        1%{?dist}
Summary:        White-and-blue animated desktop companion
License:        MIT
URL:            https://github.com/your-name/mochi-companion
Source0:        %{name}-%{version}.tar.gz
BuildArch:      noarch
Requires:       python3-gobject gtk3 gtk-layer-shell
Recommends:     wmctrl

%description
Lightweight animated robot eyes with portable and desktop-native adapters.

%prep
%autosetup

%install
install -Dm755 portable/mochi_companion.py %{buildroot}%{_bindir}/mochi-companion
install -Dm644 shared/anime_modes.json %{buildroot}%{_datadir}/mochi-companion/shared/anime_modes.json

%files
%license LICENSE
%doc README.md docs/COMPATIBILITY.md
%{_bindir}/mochi-companion
%{_datadir}/mochi-companion/shared/anime_modes.json

%changelog
* Fri Oct 02 2026 Mochi Companion contributors - 1.0.0-1
- Initial package
