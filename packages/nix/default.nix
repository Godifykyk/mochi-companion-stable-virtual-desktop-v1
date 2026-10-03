{ pkgs ? import <nixpkgs> {} }:

pkgs.stdenvNoCC.mkDerivation {
  pname = "mochi-companion";
  version = "1.0.0";
  src = ../..;

  nativeBuildInputs = [ pkgs.makeWrapper ];
  propagatedBuildInputs = [
    pkgs.python3
    pkgs.python3Packages.pygobject3
    pkgs.gtk3
    pkgs.gtk-layer-shell
  ];

  installPhase = ''
    mkdir -p $out/bin $out/share/mochi-companion/shared $out/share/applications
    cp portable/mochi_companion.py $out/bin/mochi-companion
    chmod +x $out/bin/mochi-companion
    cp shared/anime_modes.json $out/share/mochi-companion/shared/
    cp packages/common/io.github.mochi.Companion.desktop $out/share/applications/
    wrapProgram $out/bin/mochi-companion \
      --set MOCHI_DATA_DIR $out/share/mochi-companion/shared \
      --prefix GI_TYPELIB_PATH : ${pkgs.lib.makeSearchPath "lib/girepository-1.0" [ pkgs.gtk3 pkgs.gtk-layer-shell ]}
  '';

  meta = {
    description = "White-and-blue animated desktop companion";
    license = pkgs.lib.licenses.mit;
    platforms = pkgs.lib.platforms.linux;
  };
}
