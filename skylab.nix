
{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = with pkgs; [
    # Python with pip
    python312Full
    python312Packages.pip
    
    # Julia
    julia
    
    # Required for building Python packages and Julia packages
    gcc
    gfortran
    stdenv.cc.cc.lib
    
    # Additional scientific computing dependencies
    openblas

    pkg-config
    blas
    lapack
  ];

  shellHook = ''
    # Create virtual environment if it doesn't exist
    if [ ! -d .venv ]; then
      python -m venv .venv
    fi
    source .venv/bin/activate

    # Ensure pip is up to date
    pip install --upgrade pip

    # Install PyJulia
    pip install julia

    # Set JULIA_DEPOT_PATH to local directory
    export JULIA_DEPOT_PATH=$PWD/.julia

    # Set LD_LIBRARY_PATH to include libquadmath from gcc
    export LD_LIBRARY_PATH=${pkgs.gcc-unwrapped.lib}/lib:$LD_LIBRARY_PATH

    # Initialize PyJulia
    python -c "import julia; julia.install()"

    echo "Python and Julia development environment ready!"
    echo "Python version: $(python --version)"
    echo "Julia version: $(julia --version)"
    echo "You can install Python packages using pip"
    echo "You can install Julia packages using Pkg.add() in Julia"
  '';

  # Preserve PYTHONPATH and LD_LIBRARY_PATH
  NIX_LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath [
    pkgs.stdenv.cc.cc.lib
    pkgs.gcc-unwrapped.lib
    pkgs.openblas
    pkgs.lapack
  ];
  NIX_LD = pkgs.lib.fileContents "${pkgs.stdenv.cc}/nix-support/dynamic-linker";

  PYTHONPATH = "${pkgs.python312Packages.numpy}/${pkgs.python312.sitePackages}";
}
