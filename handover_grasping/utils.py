# AUTOGENERATED! DO NOT EDIT! File to edit: 02_utils.ipynb (unless otherwise specified).

__all__ = ['Image_table', 'get_grasp_line', 'get_affordancemap', 'get_model', 'get_pcd_right', 'get_pcd_left',
           'get_view', 'vis', 'get_line_len', 'width_detect']

# Cell
import math
import cv2
import numpy as np
import os
import gdown
import open3d as o3d
from matplotlib import pyplot as plt


def Image_table(col, row, img_list, title_list=None):
    """Create a Images table and show it.

    This function will show a col x row table with col x row images and titles.

    Args:
        col (str) : col of table.
        row (str) : row of table.
        img_list (list) : A list contain images [img1, img2, ..imgn].
        title_list (list) : A list contain titles [title1, title2, ..titlen].

    Returns:
        None.

    """
    if len(img_list) == (col*row):
        fig = plt.figure(figsize=(10, 10))
        pt = 0
        for i in range(1, (col*row + 1)):
            fig.add_subplot(row, col, i)
            if title_list!= None:
                plt.title(title_list[pt])
            plt.axis('off')
            plt.imshow(img_list[pt])
            pt += 1

        plt.show()
    else:
        print("Image list length is not match !")


def get_grasp_line(theta, center, depth):
    """Generate grasping two endpoints of grasping line (8cm).

    This function give two end points of a line (8cm) that project from
    3D to 2D by given line center, angle and depth image.

    Args:
      theta (float): Angle to the horizontal 0 ~ 360.
      center (list): x, y 2D coordinate
      depth (ndarray): mxn depth image (scale : micrometer)

    Returns:
        two end points of a line.
    """
    depth = depth/1000.0
    if depth[center[0], center[1]] < 0.1:
        dis_ = (np.max(depth) + np.min(depth))*0.5
        dis = dis_ - 0.199
    else:
        dis = depth[center[0], center[1]] - 0.199

    length = int((148 - int(dis*50.955))/2)

    rad = math.radians(theta)
    if theta < 90:
        x1 = int(center[1] + length*abs(math.cos(rad)))
        y1 = int(center[0] - length*abs(math.sin(rad)))
        x2 = int(center[1] - length*abs(math.cos(rad)))
        y2 = int(center[0] + length*abs(math.sin(rad)))
    else:
        x1 = int(length*abs(math.cos(rad)) + center[1])
        y1 = int(length*abs(math.sin(rad)) + center[0])
        x2 = int(center[1] - length*abs(math.cos(rad)))
        y2 = int(center[0] - length*abs(math.sin(rad)))

    p1 = (x1, y1)
    p2 = (x2, y2)

    return p1, p2

def get_affordancemap(predict, depth, ConvNet=False):
    """Generate grasping point and affordancemap.

    This function give an affordanceMap and grasping parameters for HANet and ConvNet.

    Args:
      predict (tensor): Output from HANet or ConvNet.
      depth (ndarray): mxn depth image (scale : micrometer)
      ConvNet (bool): True : for ConvNet, False : for HANet

    Returns:
        affordanceMap, grasping 2D coordinate x and y, theta
    """
    if ConvNet:
        height = depth.shape[0]
        width = depth.shape[1]
        graspable = predict[0, 2].detach().cpu().numpy()
        thes = 0

    else:
        Max = []
        Re = []
        Angle = [90,135,0,45]
        height = depth.shape[0]
        width = depth.shape[1]
        re = np.zeros((4, height, width))

        for i in range(4):
            x, y = np.where(predict[0][i] == np.max(predict[0][i]))
            re[i] = cv2.resize(predict[0][i], (width, height))
            Max.append(np.max(predict[0][i]))
            Re.append(re[i])

        theta = Angle[Max.index(max(Max))]
        graspable = re[Max.index(max(Max))]
        thes = 1

    graspable = cv2.resize(graspable, (width, height))
    depth = cv2.resize(depth, (width, height))
    graspable [depth==0] = 0
    graspable[graspable>=thes] = 0.99999
    graspable[graspable<0] = 0
    graspable = cv2.GaussianBlur(graspable, (7, 7), 0)
    affordanceMap = (graspable/np.max(graspable)*255).astype(np.uint8)
    affordanceMap = cv2.applyColorMap(affordanceMap, cv2.COLORMAP_JET)
    affordanceMap = affordanceMap[:,:,[2,1,0]]

    gray = cv2.cvtColor(affordanceMap, cv2.COLOR_RGB2GRAY)
    blurred = cv2.GaussianBlur(gray, (11, 11), 0)
    binaryIMG = cv2.Canny(blurred, 20, 160)
    contours, _ = cv2.findContours(binaryIMG, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    i = 0
    point_x = 0
    point_y = 0
    cX = 0
    cY = 0
    x = 0
    y = 0

    for c in contours:
        M = cv2.moments(c)
        if(M["m00"]!=0):
            cX = int(M["m10"] / M["m00"])
            cY = int(M["m01"] / M["m00"])
            zc = depth[cY, cX]/1000
            i += 1
            point_x += cX
            point_y += cY

    if i != 0:
        x = int(point_x / i)
        y = int(point_y / i)
    else:
        x, y = np.where(predict[0][Max.index(max(Max))] == np.max(predict[0][Max.index(max(Max))]))
        x = int(x)
        y = int(y)

    if ConvNet:
        return affordanceMap, x, y
    else:
        return affordanceMap, x, y, theta

def get_model(depth=False):
    """Download HANet pre-trained weight.

    This function is for Class HANet and HANet_depth to download pre-trained weight.

    Args:
      depth (bool): True : for HANet_depth, False : for HANet
    """
    if depth:
        url = 'https://drive.google.com/u/1/uc?id=1htAlu7-NksbH4b21xxcrVA3W-KFIIYvw'
        name = 'HANet_depth'
    else:
        url = 'https://drive.google.com/u/1/uc?id=17PBimCFf5Au1JBTYcRloMoPmwDERRfUo'
        name = 'HANet'
    path = os.path.abspath(os.getcwd())
    if not os.path.isfile(path+'/'+name + '.pth'):
        gdown.download(url, output=name + '.pth', quiet=False)

    return path + '/' + name + '.pth'

def get_pcd_right(rgb_np, depth_np, rotate_matrix=None):
    """Get pcd from RGB-D image and transfer it from camera_right to target frame

    This function take RGB-D image and convert to point cloud by opend3d.

    Args:
      rgb_np (ndarray) : RGB image (mxnx3).
      depth_np (ndarray) : DEPTH image (mxn).
      rotate_matrix (list) : 4x4 transfer matrix for camera_right optical frame to target frame.

    Returns:
        pointcloud and frame tf.
    """
    axis = o3d.geometry.TriangleMesh.create_coordinate_frame(size=0.3, origin=[0,0,0])
    rgb = o3d.geometry.Image(rgb_np)
    depth = o3d.geometry.Image(depth_np)

    rgbd = o3d.geometry.RGBDImage.create_from_color_and_depth(rgb, depth, convert_rgb_to_intensity=False)
    pcd1 = o3d.geometry.PointCloud.create_from_rgbd_image(rgbd, o3d.camera.PinholeCameraIntrinsic(o3d.camera.PinholeCameraIntrinsicParameters.PrimeSenseDefault))
    points1 = np.asarray(pcd1.points)
    pcd_sel1 = pcd1.select_by_index(np.where((points1[:, 2] > 0.25)&(points1[:, 2] < 1.3))[0])

    if rotate_matrix != None:
        pcd_sel1.transform(rotate_matrix)
        axis.transform(rotate_matrix)

    return pcd_sel1, axis

def get_pcd_left(rgb_np, depth_np, rotate_matrix):
    """Get pcd from RGB-D image and transfer it from camera_left to target frame

    This function take RGB-D image and convert to point cloud by opend3d.

    Args:
      rgb_np (ndarray) : RGB image (mxnx3).
      depth_np (ndarray) : DEPTH image (mxn).
      rotate_matrix (list) : 4x4 transfer matrix for camera_right optical frame to target frame.

    Returns:
        pointcloud and frame tf.
    """
    axis = o3d.geometry.TriangleMesh.create_coordinate_frame(size=0.3, origin=[0,0,0])
    rgb = o3d.geometry.Image(rgb_np)
    depth = o3d.geometry.Image(depth_np)

    rgbd = o3d.geometry.RGBDImage.create_from_color_and_depth(rgb, depth, convert_rgb_to_intensity=False)
    pcd2 = o3d.geometry.PointCloud.create_from_rgbd_image(rgbd, o3d.camera.PinholeCameraIntrinsic(o3d.camera.PinholeCameraIntrinsicParameters.PrimeSenseDefault))
    points2 = np.asarray(pcd2.points)
    pcd_sel2 = pcd2.select_by_index(np.where((points2[:, 2] < 2)&(points2[:, 0] < 1.5))[0])

    if rotate_matrix != None:
        pcd_sel2.transform(rotate_matrix)
        axis.transform(rotate_matrix)

    return pcd_sel2, axis

def get_view(pcd1, pcd2, front, lookat, up, zoom, view_id):
    """Generate multi-view RGB-D image from pointclouds

    This function take 2 pointclouds(in same frame) and get image in specific view parameters.

    Args:
        front (list) : 1x3 vector.
        lookat (list) : 1x3 vector.
        up (list) : 1x3 vector.
        zoom (float) : a float number to define zoom.
        view_id : position of virtual view

    Returns:
        RGB and Depth images.
    """
    vis = o3d.visualization.Visualizer()
    vis.create_window(visible=False)
    vis.get_render_option().point_color_option = o3d.visualization.PointColorOption.Color
    vis.add_geometry(pcd1)
    vis.update_geometry(pcd1)
    vis.add_geometry(pcd2)
    vis.update_geometry(pcd2)
    ctr = vis.get_view_control()
    ctr.set_lookat(lookat[view_id])
    ctr.set_front(front[view_id])
    ctr.set_up(up[view_id])
    ctr.set_zoom(zoom[view_id])
    opt = vis.get_render_option()
    opt.background_color = np.asarray([0, 0, 0])
    vis.update_renderer()
    vis.poll_events()
    image = vis.capture_screen_float_buffer(True)
    depth = vis.capture_depth_float_buffer(True)

    img = np.array(image)[414:695,740:1181]
    depth = np.array(depth)[414:695,740:1181]
    img = cv2.resize(img, (640,480))
    depth = cv2.resize(depth, (640,480))

    return img*255, depth

def vis(pcd_list, show_axis=False):
    """visualize pointcloud

    This function take multiple pointclouds and show all of them by opend3d.

    Args:
      pcd_list (list) : list contain pcds [pcd1, pcd2,...,pcdn].
      show_axis (bool) : Show frame tf ot not.
    """
    axis = o3d.geometry.TriangleMesh.create_coordinate_frame(size=0.3, origin=[0,0,0])
    vis = o3d.visualization.Visualizer()
    vis.create_window(visible=True)
    vis.get_render_option().point_color_option = o3d.visualization.PointColorOption.Color
    for pcd in pcd_list:
        vis.add_geometry(pcd)
        vis.update_geometry(pcd)
    if show_axis:
        vis.add_geometry(axis)
        vis.update_geometry(axis)
    ctr = vis.get_view_control()
    opt = vis.get_render_option()
    opt.background_color = np.asarray([0, 0, 0])
    vis.update_renderer()
    vis.poll_events()
    vis.run()
    vis.destroy_window()

def get_line_len(center, depth):
    """Generate grasping two endpoints of grasping line(8cm).

    Inputs:
      theta: degree
      center: x, y coordinate
      depth: depth image (mm)
    """
    depth = depth/1000.0
    if depth[center[0], center[1]] < 0.1:
        dis_ = (np.max(depth) + np.min(depth))*0.5
        dis = dis_ - 0.199
    else:
        dis = depth[center[0], center[1]] - 0.199

    length = int((148 - int(dis*50.955))/2)

    return length

def width_detect(depth, center, theta):
    """Compute surface width

    This function compute surface width according to grasping center.

    Args:
        depth (ndarray) : depth image (mm).
        center: x, y coordinate
        theta : degrees (0, 90, +-45)

    Returns:
        width.
    """
    if np.max(depth) < 10:
        depth = depth*1000
    dis_center = int(depth[center[0], center[1]])
    if dis_center == 0.0:
        dis_center = 313
    depth_line = [dis_center]

    is_width_r = True
    is_width_l = True

    height = 480
    width = 640

    lan = 0

    thes_depth = 100

    i = 0

    LAN = get_line_len(center, depth)
    LAN = LAN*1.8

    while is_width_l == True or is_width_r == True:
        if theta == 0:
            r_pos = center[1] + i
            l_pos = center[1] - i

            c_r = (r_pos, center[0])
            c_l = (l_pos, center[0])

            if abs(r_pos) < width:
                dis_r = int(depth[center[0], r_pos])
            else:
                is_width_r = False
            if abs(l_pos) < width:
                dis_l = int(depth[center[0], l_pos])
            else:
                is_width_l = False

        elif theta == 90:
            r_pos = center[0] + i
            l_pos = center[0] - i

            if abs(r_pos) < height:
                dis_r = int(depth[r_pos, center[1]])
            else:
                is_width_r = False
            if abs(l_pos) < height:
                dis_l = int(depth[l_pos, center[1]])
            else:
                is_width_l = False

            c_r = (center[1], r_pos)
            c_l = (center[1], l_pos)

        elif theta == 45:
            r_pos_x = center[0] + i
            r_pos_y = center[1] - i

            l_pos_x = center[0] - i
            l_pos_y = center[1] + i

            if abs(r_pos_x) < 480 and abs(r_pos_y) < 640:
                dis_r = int(depth[r_pos_x, r_pos_y])
            else:
                is_width_r = False
            if abs(l_pos_x) < 480 and abs(l_pos_y) < 640:
                dis_l = int(depth[l_pos_x, l_pos_y])

            c_r = (r_pos_y, r_pos_x)
            c_l = (l_pos_y, l_pos_x)

        elif theta == -45:
            r_pos_x = center[0] + i
            r_pos_y = center[1] + i

            l_pos_x = center[0] - i
            l_pos_y = center[1] - i

            if abs(r_pos_x) < 480 and abs(r_pos_y) < 640:
                dis_r = int(depth[r_pos_x, r_pos_y])
            else:
                is_width_r = False
            if abs(l_pos_x) < 480 and abs(l_pos_y) < 640:
                dis_l = int(depth[l_pos_x, l_pos_y])
            else:
                is_width_l = False

            c_r = (r_pos_y, r_pos_x)
            c_l = (l_pos_y, l_pos_x)

        depth_line.insert(0, dis_l)
        depth_line.append(dis_r)

        if dis_r != 0:
            if (abs(dis_center-dis_r) < thes_depth) and (is_width_r==True):
                lan += 1
            else:
                is_width_r = False

        if dis_l != 0:
            if (abs(dis_center-dis_l) < thes_depth) and (is_width_l==True):
                lan += 1
            else:
                is_width_l = False


        i += 1

    return lan - LAN