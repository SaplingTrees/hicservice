import cooler
import h5py
from pathlib import Path

import numpy as np
from fastapi import HTTPException

TILE_SIZE = 256


class CoolFile:
    filepath = ""
    name = ""
    is_multires = True
    n_levels = 1
    resolutions = []
    sizes = []

    def __init__(self, path: Path):
        self.filepath = path
        self.name = path.stem
        self.open(path)

    def open(self, filepath):
        if cooler.fileops.is_cooler(str(filepath)) and filepath.suffix != ".mcool":
            self.is_multires = False
            self.n_levels = 1
            info = cooler.Cooler(str(filepath)).info
            self.resolutions = [info['bin-size']]
            self.sizes = [info['nbins']]
        else:
            with h5py.File(str(filepath), "r") as f:
                self.is_multires = True
                resolutions = [int(res) for res in f["resolutions"].keys()]
                resolutions.sort(reverse=True)
                self.n_levels = len(resolutions)
                self.resolutions = list(resolutions)
            sizes = []
            for resolution in self.resolutions:
                c: cooler.Cooler = cooler.Cooler(str(filepath) + "::/resolutions/" + str(resolution))
                sizes.append(int(c.info['nbins']))
            self.sizes = sizes

    def get_identifier(self):
        return self.name

    def get_info(self):
        return {
            "multires": self.is_multires,
            "levels": self.n_levels,
            "resolutions": self.resolutions,
            "sizes": self.sizes,
            "tile_size": TILE_SIZE
        }

    def open_cooler(self, level):
        if level >= self.n_levels:
            raise HTTPException(status_code=404, detail=f"Attempted to open cooler with level out of bounds.")

        if self.is_multires:
            return cooler.Cooler(str(self.filepath) + "::resolutions/" + str(self.resolutions[level]))
        else:
            return cooler.Cooler(str(self.filepath))

    def create_tile(self, level, start_x, end_x, start_y, end_y, balanced=False):
        c = self.open_cooler(level)
        data = c.matrix(balance=balanced)
        # TODO: Probably add some safeguards to ensure that start and end values are in bounds of the matrix...
        # TODO 2: Should check how doing the slicing in this way handles cells with no entries
        #  Should be NaNs, but likely will be 0, in which case i need to use a different access method...
        return data[start_y:end_y, start_x:end_x]

    def get_tile(self, level, tile_x, tile_y, balanced=False, pad=True):
        if level >= self.n_levels:
            raise ValueError(f"Attempted to fetch tile from level out of bounds.")

        start_x = tile_x * TILE_SIZE
        start_y = tile_y * TILE_SIZE

        tile = self.create_tile(level, start_x, start_x + TILE_SIZE, start_y, start_y + TILE_SIZE, balanced)

        if not pad:
            return tile

        height, width = tile.shape
        pad_h = max(0, TILE_SIZE - height)
        pad_w = max(0, TILE_SIZE - width)

        return np.pad(
            tile.astype(float),
            ((0, pad_h), (0, pad_w)),
            mode='constant',
            constant_values=np.nan
        )

    def get_region_pos(self, level, start_x, end_x, start_y, end_y, balanced=False):
        if level >= self.n_levels:
            raise ValueError(f"Attempted to fetch tile from level out of bounds.")

        return self.create_tile(level, start_x, end_x + 1, start_y, end_y + 1, balanced)

    def get_region(self, level, region_start_x, region_end_x, region_start_y, region_end_y, balanced=False):
        if level >= self.n_levels:
            raise ValueError(f"Attempted to fetch tile from level out of bounds.")

        resolution = self.resolutions[level]
        return self.create_tile(level,
                                region_start_x // resolution, (region_end_x + resolution) // resolution,
                                region_start_y // resolution, (region_end_y + resolution) // resolution, balanced)
