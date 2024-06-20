"""
.. _voxelize_surface_mesh_example:

Voxelize a Surface Mesh
~~~~~~~~~~~~~~~~~~~~~~~

Create a voxel model (like legos) of a closed surface or volumetric mesh.

"""


#    docker run -it -v ${pwd}/simulation_results:/app/simulation_results  simucell3d_docker_img:latest ../parameters_default_dynamic_dan.xml



import numpy as np
import pyvista as pv
import matplotlib.pyplot as plt
import matplotlib.collections as collections

from tqdm import tqdm
from tifffile import imwrite
from pathlib import Path
import os
import shutil
from line_profiler_pycharm import profile

def round_to_nearest(value, base):
    value = np.asarray(value)

    value /= base
    value = np.round(value)
    value *= base
    return value

input_dir =  Path.cwd().joinpath(r"simulation_results/dynamic_simulation/face_data")

output_dir = Path(os.path.join(input_dir.parent, "voxelized"))
shutil.rmtree(output_dir, ignore_errors=True)
output_dir.mkdir(parents=True, exist_ok=True)


meshfiles = sorted(Path(input_dir).iterdir(), key=os.path.getmtime, reverse=True)

for meshfile in tqdm(meshfiles, unit=" files", position=0, leave=True):
    if meshfile.suffix.endswith(".vtk"):

        print(f"Reading {meshfile}")
        mesh = pv.read(meshfile)

        # print(mesh.array_names)
        mesh.set_active_scalars('face_cell_id')
        surf = mesh.extract_surface()


        CameraPosition = (-0.00028617924571107807, 1.2141999718551233e-05, 1.2238500858074985e-05)
        CameraFocalPoint = (1.2123850410716841e-05, 1.2141999718551233e-05, 1.2238500858074985e-05)
        CameraViewUp = (0.0, 0.0, 1.0)
        cpos = [CameraPosition, CameraFocalPoint, CameraViewUp]
        # mesh.plot(scalars='face_cell_id', cpos=cpos, opacity=0.99, specular=0.3)

        volume = np.zeros((3, 128, 128), dtype=np.uint16)


        # mesh_coords = mesh.cell_centers().points
        # mesh_values = mesh.get_array('face_cell_id')
        # vol_x = np.linspace(0, 1, volume.shape[2])
        # vol_y = np.linspace(0, 1, volume.shape[1])
        # vol_z = np.linspace(0, 1, volume.shape[0])
        #
        # v_xi, v_yi, v_zi = np.meshgrid(vol_x, vol_y, vol_z, indexing='xy')
        #
        # # interpolate
        # interp = LinearNDInterpolator(mesh_coords, mesh_values)
        #
        # volume = interp(vol_x, vol_y, vol_z)
        # np.griddata(mesh_coords, mesh_values, (v_xi, v_yi, v_zi), method='linear')

        center = np.array([0,0,0])
        slice_normal = np.array([0, 0, 1])   # stupid (x,y,z)
        point_a = center + slice_normal * 1e-4
        point_b = center - slice_normal * 1e-4
        z_slice_locations = pv.Line(point_a, point_b, resolution=volume.shape[0]-1)

        # p = pvqt.BackgroundPlotter()
        # pv.global_theme.allow_empty_mesh = True
        # p.show_bounds(grid=True, location='back')
        # p.title = f'{meshfile.stem}'

        name = 'face_cell_id'
        cm = plt.colormaps['tab20c']
        plt.style.use('dark_background')


        for z_slice_idx, line_point in enumerate(z_slice_locations.points):
            slice = surf.slice(normal=slice_normal, origin=line_point)
            verts = surf.clip_closed_surface(normal=slice_normal, origin=line_point)
            # p.add_mesh(slice)

            unique_cell_ids = np.unique(slice[name]).astype(int)
            dpi = 1000
            fig, ax = plt.subplots(figsize=(volume.shape[2]/dpi, volume.shape[1]/dpi), dpi=dpi)
            for color_idx, unique_cell_id in enumerate(unique_cell_ids):
                single_outline = slice.threshold([unique_cell_id, unique_cell_id], scalars=name).extract_surface()
                single_verts = mesh.threshold([unique_cell_id, unique_cell_id], scalars=name).extract_surface().clip_closed_surface(normal=slice_normal, origin=line_point).clip(normal=-1 * slice_normal, origin=line_point)

                patches = []
                for i in range(single_verts.n_cells):
                    x_patch_verts = single_verts.get_cell(i).points[:, 0]
                    y_patch_verts = single_verts.get_cell(i).points[:, 1]
                    patch_verts = np.array([x_patch_verts, y_patch_verts]).transpose()

                    patches.append(patch_verts)

                starts = single_outline.lines[1:][::3]
                ends = single_outline.lines[2:][::3]
                x_starts = single_outline.points[starts][:, 0]
                y_starts = single_outline.points[starts][:, 1]
                x_ends = single_outline.points[ends][:, 0]
                y_ends = single_outline.points[ends][:, 1]

                x = np.vstack([x_starts, x_ends])
                y = np.vstack([y_starts, y_ends])

                segments = np.array([x, y]).transpose()

                # Create a LineCollection object
                Blue = unique_cell_id & 255
                Green = (unique_cell_id >> 8) & 255
                Red = (unique_cell_id >> 16) & 255

                color = (Red / 255, Green / 255, Blue / 255)
                lc = collections.LineCollection(segments, colors=color, antialiased=False, linewidths=.1, facecolors=color)
                # ax.add_collection(lc)


                pc = collections.PolyCollection(patches, facecolors=color, antialiased=False, closed=True)
                ax.add_collection(pc)


            ax.set_xlim([mesh.bounds[0], mesh.bounds[1]])
            ax.set_ylim([mesh.bounds[2], mesh.bounds[3]])
            ax.axis('off')
            # plt.show()

            fig.canvas.draw()

            # Convert the canvas to a raw RGB buffer, next go back to the u16 we wanted.
            buf = fig.canvas.renderer.buffer_rgba()
            ncols, nrows = fig.canvas.get_width_height()
            image = np.frombuffer(buf, dtype=np.uint8).reshape(nrows, ncols, 4).astype(int)
            r = image[:, :, 0]
            g = image[:, :, 1]
            b = image[:, :, 2]

            plt.close()

            slab = r * 256**2 + g * 256 + b     # convert RGB back to face_cell_id

            volume[z_slice_idx, :, :] = slab    # assign to the slice in the volume
    output_file = Path(f'{output_dir}/{meshfile.stem}.tif')
    imwrite(output_file, volume.astype(np.uint16))
