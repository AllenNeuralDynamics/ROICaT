import matplotlib.pyplot as plt
from ipywidgets import interact, widgets
import seaborn as sns


import numpy as np
import sparse
import scipy.sparse

import copy

from . import helpers

def display_toggle_image_stack(
    images,
    fig=None,
    ax=None,
    clim=None,
    **imshow_kwargs
):
    """
    Display a stack of images using a slider.
    REQUIRES use of Jupyter Notebook.
    RH 2022

    Args:
        images (np.ndarray):
            Stack of images.
            Shape: (num_frames, height, width)
            Optionally, shape: (num_frames, height, width, num_channels)
        fig (matplotlib.figure.Figure, optional):
            Figure to use.
        ax (matplotlib.axes.Axes, optional):
            Axes to use.
        clim (tuple, optional):
            Color limits.
        kwargs (dict, optional):
            Keyword arguments to pass to imshow.
    """

    if ax is None:
        fig = plt.figure()
        ax = fig.add_subplot(1, 1, 1)

    imshow_FOV = ax.imshow(
        images[0],
        **imshow_kwargs
    )

    def update(i_frame = 0):
        fig.canvas.draw_idle()
        imshow_FOV.set_data(images[i_frame])
        imshow_FOV.set_clim(clim)


    interact(update, i_frame=widgets.IntSlider(min=0, max=len(images)-1, step=1, value=0));


def display_toggle_2channel_image_stack(images, clim=None):

    fig, axs = plt.subplots(1,2 , figsize=(14,8))
    ax_1 = axs[0].imshow(images[0][...,0], clim=clim)
    ax_2 = axs[1].imshow(images[0][...,1], clim=clim)

    def update(i_frame = 0):
        fig.canvas.draw_idle()
        ax_1.set_data(images[i_frame][...,0])
        ax_2.set_data(images[i_frame][...,1])


    interact(update, i_frame=widgets.IntSlider(min=0, max=len(images)-1, step=1, value=0));


def compute_colored_FOV(
    spatialFootprints,
    FOV_height,
    FOV_width,
    labels,
    cmap='random',
    boolSessionID=None,
    alphas=None,
):
    """
    Computes a set of images of FOVs of spatial footprints, colored
     by the predicted class.

    Args:
        spatialFootprints (list of scipy.sparse.csr_matrix or scipy.sparse.csr_matrix):
            If list, then each element is all the spatial footprints for a given session.
            If scipy.sparse.csr_matrix, then this is all the spatial footprints for all 
             sessions, and boolSessionID must be provided.
        FOV_height (int):
            Height of the field of view
        FOV_width (int):
            Width of the field of view
        labels (list of arrays or array):
            Label (will be a unique color) for each spatial footprint.
            If list, then each element is all the labels for a given session.
            If array, then this is all the labels for all sessions, and 
             boolSessionID must be provided.
        cmap (str or matplotlib.colors.ListedColormap):
            Colormap to use for the labels.
            If 'random', then a random colormap is generated.
            Else, this is passed to matplotlib.colors.ListedColormap.
        boolSessionID (np.ndarray of bool):
            Boolean array indicating which session each spatial footprint belongs to.
            Only required if spatialFootprints and labels are not lists.
            shape: (n_roi_total, n_sessions)
        alphas (np.ndarray):
            Alpha value for each label.
            shape (n_labels,) which is the same as the number of unique labels len(np.unique(labels))
    """
    labels_cat = np.concatenate(labels) if (isinstance(labels, list) and (isinstance(labels[0], list) or isinstance(labels[0], np.ndarray))) else labels.copy()
    if alphas is None:
        alphas = np.ones(len(labels_cat))
    
    h, w = FOV_height, FOV_width

    rois = scipy.sparse.vstack(spatialFootprints)
    rois = rois.multiply(1.2/rois.max(1).A).power(1)

    u = np.unique(labels_cat)

    n_c = len(u)

    if n_c > 1:
        colors = helpers.rand_cmap(nlabels=n_c, verbose=False)(np.linspace(0.,1.,n_c, endpoint=True)) if cmap=='random' else cmap(np.linspace(0.,1.,n_c, endpoint=True))
        colors = colors / colors.max(1, keepdims=True)
    else:
        colors = np.array([[0,0,0,0]])

    if np.isin(-1, labels_cat):
        colors[0] = [0,0,0,0]

    labels_squeezed = helpers.squeeze_integers(labels_cat)
    labels_squeezed -= labels_squeezed.min()

    rois_c = scipy.sparse.hstack([rois.multiply(colors[labels_squeezed, ii][:,None]) for ii in range(4)]).tocsr()
    rois_c.data = np.minimum(rois_c.data, 1)

    ## apply alpha
    rois_c = rois_c.multiply(alphas[labels_squeezed][:,None]).tocsr()

    boolSessionID = np.concatenate([[np.arange(len(labels))==ii]*len(labels[ii]) for ii in range(len(labels))] , axis=0) if boolSessionID is None else boolSessionID
    rois_c_bySessions = [rois_c[idx] for idx in boolSessionID.T]

    rois_c_bySessions_FOV = [r.max(0).toarray().reshape(4, h, w).transpose(1,2,0)[:,:,:3] for r in rois_c_bySessions]

    return rois_c_bySessions_FOV


def crop_cluster_ims(ims):
    """
    Crops the images to the smallest rectangle containing all non-zero pixels.
    RH 2022

    Args:
        ims (np.ndarray):
            Images to crop.

    Returns:
        np.ndarray:
            Cropped images.
    """
    ims_max = np.max(ims, axis=0)
    z_im = ims_max > 0
    z_where = np.where(z_im)
    z_top = z_where[0].max()
    z_bottom = z_where[0].min()
    z_left = z_where[1].min()
    z_right = z_where[1].max()
    
    ims_copy = copy.deepcopy(ims)
    im_out = ims_copy[:, max(z_bottom-1, 0):min(z_top+1, ims.shape[1]), max(z_left-1, 0):min(z_right+1, ims.shape[2])]
    im_out[:,(0,-1),:] = 1
    im_out[:,:,(0,-1)] = 1
    return im_out


def confusion_matrix(cm, **params):
    default_params = dict(
        annot=True,
        annot_kws={"size": 16},
        vmin=0.,
        vmax=1.,
        cmap=plt.get_cmap('gray')
    )
    for key in params:
        default_params[key] = params[key]
    sns.heatmap(cm, **default_params)