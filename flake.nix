{
  description = "DANDI native build dev environment";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs";

  outputs = { self, nixpkgs }:
    let
      pkgs = nixpkgs.legacyPackages.x86_64-linux;
    in
    {
      devShells.x86_64-linux.default = pkgs.mkShell {
        buildInputs = with pkgs; [
          # Python 3.13
          python313Packages.python

          # Docker and Docker Compose
          docker

          # Postgres stuff
          postgresql
          libpqxx
        ];

        shellHook = ''
          source ./venv/bin/activate
          source ./dev/export-env.sh
        '';
      };
    };
}
