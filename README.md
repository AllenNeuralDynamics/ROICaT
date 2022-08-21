# ROICaT
Region Of Interest Classification and Tracking

A simple to use pipeline designed for classifying images of cells and tracking them across imaging planes/sessions.
Currently designed to use with Suite2p output data (stat.npy and ops.npy files).

TODO:
- add tracking to repo
- add classification to repo
- unify and refactor backend
- add CaImAn support
- integration tests
- make demo notebooks
- port demo notebooks to CoLab
- make reference API
- make nice README.md


Installation
------------

```
git clone url.to.repo
cd path/to/ROICaT/directory

conda create -n ROICaT python=3.9
conda activate ROICaT

pip3 install torch torchvision torchaudio --extra-index-url https://download.pytorch.org/whl/cu113
pip install -r requirements.txt
conda install pytorch-sparse -c pyg
```