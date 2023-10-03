import os

import warnings
import pytest
import tempfile
import requests

import numpy as np
import torch
import multiprocessing as mp

from roicat import visualization
import holoviews as hv
from bokeh.server.server import Server
from bokeh.application import Application
from bokeh.application.handlers.function import FunctionHandler

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

hv.extension("bokeh")


def create_mock_input():
    ## Create mock input. Looks dumb. But it's just a test.
    mock_data = np.array([[0, 0], [1, 0], [0, 1], [1, 1]], dtype=np.float32)
    mock_idx_images_overlay = torch.tensor([0, 1, 2, 3])
    mock_images_overlay = np.random.rand(4, 2, 2)
    return mock_data, mock_idx_images_overlay, mock_images_overlay


def get_indices():
    ## Steal the fn_get_indices function for testing purposes
    path_tempFile = os.path.join(tempfile.gettempdir(), "indices.csv")
    with open(path_tempFile, "r") as f:
        indices = f.read().split(",")
    indices = [int(i) for i in indices if i != ""] if len(indices) > 0 else None
    return indices


def start_server(apps):
    ## Start Bokeh server given a test scatter plot
    server = Server(
        apps,
        port=5006,
        address="0.0.0.0",
        allow_websocket_origin=["0.0.0.0:5006", "localhost:5006"],
    )
    server.start()

    ## Setup IO loop
    server.io_loop.start()


def deploy_bokeh(instance):
    ## Draw test plot and add to Bokeh document
    hv.extension("bokeh")

    ## Create a mock input
    mock_data, mock_idx_images_overlay, mock_images_overlay = create_mock_input()

    ## Create a scatter plot
    _, layout, path_tempFile = visualization.select_region_scatterPlot(
        data=mock_data,
        idx_images_overlay=mock_idx_images_overlay,
        images_overlay=mock_images_overlay,
        size_images_overlay=0.01,
        frac_overlap_allowed=0.5,
        figsize=(1200, 1200),
        alpha_points=1.0,
        size_points=10,
        color_points="b",
    )

    ## Sanity check
    warnings.warning("path_tempFile: {}".format(path_tempFile))
    warnings.warn("Tmpfile dir: {}".format(os.listdir(tempfile.gettempdir())))
    assert os.path.exists(path_tempFile)

    ## Render plot
    hv_layout = hv.render(layout)
    hv_layout.name = "drawing_test"

    ## Add to Bokeh document
    instance.add_root(hv_layout)


def check_server():
    try:
        # response = requests.get("http://127.0.0.1:5006")
        response = requests.get("http://localhost:5006")
        if response.status_code == 200:
            warnings.warn("Server is up and running!")
        else:
            warnings.warn(f"Server responded with status code: {response.status_code}")
    except requests.ConnectionError:
        warnings.warn("Cannot connect to the server!")


def test_interactive_drawing():
    # try:
    warnings.warn("Interactive GUI Drawing Test is running. Please wait...")
    ## Bokeh server deployment at http://localhost:5006
    apps = {"/": Application(FunctionHandler(deploy_bokeh))}

    warnings.warn("Deploy Bokeh server to localhost:5006...")
    ## Let it run in the background so that the test can continue
    server_process = mp.Process(target=start_server, args=(apps,))
    server_process.start()

    ## Check if the server is up and running
    warnings.warn("Check if Bokeh server is up and running...")
    check_server()

    warnings.warn("Setup chrome webdriver...")
    service = Service()
    chrome_options = Options()
    chrome_options.add_argument("--window-size=1280,1280")
    ## For local testing, just comment out the headless options.
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")

    ## if you are on latest version say selenium v4.6.0 or higher, you don't have to use third party library such as WebDriverManager
    warnings.warn("Driver parameter sanity check...")
    driver = webdriver.Chrome(service=service, options=chrome_options)
    capabilities = driver.capabilities
    warnings.warn("Browser Name: {}".format(capabilities.get("browserName")))
    warnings.warn("Browser Version: {}".format(capabilities.get("browserVersion")))
    warnings.warn("Platform Name: {}".format(capabilities.get("platformName")))
    warnings.warn(
        "Chrome Driver Version: {}".format(
            capabilities.get("chrome").get("chromedriverVersion")
        )
    )

    warnings.warn("Get to the Bokeh server...")
    # driver.get("http://127.0.0.1:5006/")
    driver.get("http://localhost:5006/")
    wait = WebDriverWait(driver, 10)
    warnings.warn("Found the Bokeh server, locate drawing Bokeh element...")
    try:
        element = wait.until(EC.presence_of_element_located((By.XPATH, "//*")))
        warnings.warn("Found Bokeh drawing element!")
    except Exception as e:
        warnings.warn(f"Failed to locate element: {str(e)}")

    ## Create movement set
    size = element.size
    width, height = size["width"], size["height"]

    ## Move to the center of the element
    warnings.warn("Start mouse movement...")
    actions = ActionChains(driver)
    actions.move_to_element(element)
    actions.click_and_hold()

    ## Draw!
    actions.move_by_offset(
        int(width / 2), int(0)
    )  ## Move from center to midpoint of right edge
    actions.move_by_offset(
        int(0), int(-height / 2)
    )  ## Move from midpoint of right edge to top right corner
    actions.move_by_offset(
        int(-width / 2), int(0)
    )  ## Move from top right corner to midpoint of top edge
    actions.release()
    actions.perform()

    warnings.warn("Mouse movement done! Detach Selenium from Bokeh server...")
    driver.quit()

    warnings.warn("Test if indices are correctly saved...")
    warnings.warn("Tmpfile dir: {}".format(os.listdir(tempfile.gettempdir())))
    indices = get_indices()
    assert indices == [3]
    # except Exception as e:
    #     warnings.warn(f"Test failed: {str(e)}")
    #     raise e
    # finally:
    warnings.warn("Test is done. Cleaning up...")
    server_process.terminate()
    server_process.join()
    warnings.warn("Test is done. Cleaning up done.")
