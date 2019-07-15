import cv2
import numpy as np
from PIL import Image
from skimage.transform.integral import integral_image, integrate
from random import randint

def is_white_patch(cur_patch,white_percentage):
    ''' Basic is_white check: checks if the extracted patch is white
        and returns True if so

    input:
    cur_patch, patch to check
    white_percentage, white portion threshold

    output:
    True if percentage of white> white portion threshold
    False otherwise
    '''
    #good buttt slowww
    # half black and half white patches are still kept. not a good thing.
    is_white = True
    total_white = float(cur_patch.shape[0] *cur_patch.shape[1] * cur_patch.shape[2] * 255)
    if (cur_patch.sum()/total_white)>white_percentage:
        return is_white
    else:
        return not is_white

def patch_sampling_using_integral(slide, mask, **opts):
    """Patch sampling on whole slide image

    Arguments
    +++++++++

    slide = OpenSlide Object
    mask = mask image ( 0-1 int type nd-array)

    Keyword arguments
    +++++++++++++++++

    :param obj logger: a pymod:logging instance

    slide_level = level of mask

    patch_size = size of patch scala integer n
    patch_num = the number of output patches

    ...fix me!

    return: list of patches (RGB images), list of patch point (starting from left top)
    """
    # def values updated from **opts
    dopts = {
        'slide_level' : 5,
        'patch_size' : 224,
        'patch_num' : 100,
        'white_threshold' : .3,
        'white_threshold_incr' : .05,
        'white_threshold_max' : .7,
        'area_overlap' : .6,
        'bad_batch_size' : 500,
        'logger' : None,
    }
    for dk in dopts:
        try:
            dopts[dk] = opts.pop(dk, None)
        except KeyError as k:
            pass
        # reinject as standard var
        exec "{} = dopts[dk]".format(dk)

    if opts:
        # leftovers...
        raise RuntimeError('unexpected options {}'.format(opts))

    logger.debug("kw opts:\n{}.".format(dopts))

    patch_list = []
    patch_point = []
    # taking the nonzero points in the mask
    x_l, y_l = mask.nonzero()

    # [BUG] Why no else branch?
    # Go on if the nonzero list is big enough for at least 2 patches.
    if len(x_l) > patch_size / slide.level_downsamples[slide_level] * 2:
        # patch size at given level or resolution
        level_patch_size = int(patch_size / slide.level_downsamples[slide_level])
        # computing the actual level of resolution
        # applying the nonzero mask as a dot product
        x_ws = (np.round(x_l * slide.level_downsamples[slide_level])).astype(int)
        y_ws = (np.round(y_l * slide.level_downsamples[slide_level])).astype(int)
        cnt = 0         # good patch counter
        nt_cnt = 0      # not taken patch counter
        while(cnt < patch_num):
            # sampling from random distribution
            p_idx = randint(0, len(x_l) - 1)
            # picking the random point in the mask
            level_point_x, level_point_y = x_l[p_idx], y_l[p_idx]
            # [BUG] otsu threshold takes also border, so discard?? mmh, needs
            # double check (risk missing stuff...) Please, parametrize, zero default.
            if (level_point_y < 50) or (level_point_x < 250):
                continue

            # boundary check: discard coordinates on mask's border (it
            # shouldn't be necessary in sliding window mode, TBD...). Artifact
            # of random coordinates (!?)
            check_bound = np.resize(
                np.array(
                    [level_point_x + level_patch_size, level_point_y + level_patch_size]
                ), (2,)
            )
            if check_bound[0] > mask.shape[0] or check_bound[1] > mask.shape[1]:
                logger.debug(
                    'Coordinate(s) out of mask boundary: {} ?> {}, {} ?> {}'.format(
                        check_bound[0], mask.shape[0], check_bound[1], mask.shape[1]
                    )
                )
                continue

            # make patch from mask image
            level_patch_mask = mask[
                int(level_point_x) : int(level_point_x + level_patch_size),
                int(level_point_y) : int(level_point_y + level_patch_size)
            ]

            # apply integral
            ii_map = integral_image(level_patch_mask)
            ii_sum = integrate(ii_map, (0, 0), (level_patch_size - 1, level_patch_size - 1))

            # total patch area should covers at least x% of the annotation
            # region
            overlap = float(ii_sum) / (level_patch_size**2)
            if overlap < area_overlap:
                continue

            # square patch (RGB point array in [0, 255])
            patch = slide.read_region(
                (y_ws[p_idx], x_ws[p_idx]), 0, (patch_size, patch_size)
            )
            patch = np.array(patch)

            if np.sum(patch) == 0:
                logger.info('Skipping black patch at {}, {}'.format(level_point_x, level_point_y))
                continue

            # check almost white RGB values
            white_mask = patch[:,:,0:3] > 200
            # sum over the 3 RGB channels
            if float(np.sum(white_mask)) / (patch_size**2*3) <= white_threshold:
                # got a good one...
                patch_list.append(cv2.cvtColor(patch, cv2.COLOR_RGBA2BGR))
                # ...with its location
                patch_point.append((x_l[p_idx], y_l[p_idx]))
                cnt += 1
            else:
                # got a bad one
                nt_cnt += 1

            # too many bad ones in this batch, tweak it
            if nt_cnt >= bad_batch_size:
                if white_threshold >= white_threshold_max:
                    logger.warning('Max white threshold reached! Bailing out')
                    break

                white_threshold += white_threshold_incr
                nt_cnt = 0
                logger.debug(
                    'white_threshold += {}, now at {}'.format(
                        white_threshold_incr, white_threshold
                    )
                )
        # {end while}
    # {end if}

    def_pl = []
    def_pp = []

    for i in range(len(patch_list)):
        # [BUG] parameterize grey threshold. Discard too grey one. Move inside main loop
        if np.mean(patch_list[i]) > 90:
            def_pl.append(patch_list[i])
            def_pp.append(patch_point[i])

    # give out patch list and coordinate list
    return def_pl, def_pp


def tumor_patch_sampling_using_centerwin(
        slide, slide_level, mask, patch_size, patch_num
):
    """
    [??? original code. Never used]

    tumor patch sampling using center window
    plz input the only tumor mask
    it will malfunctioned if you input normal mask or tissue mask

    input parameters are same as patch_sampling_using_integral
    """

    raise RuntimeError('Unrevised code')

    patch_list = []
    patch_point = []
    window_size = int(32/ slide.level_downsamples[slide_level])

    x_l,y_l = mask.nonzero()
    if len(x_l) > patch_size*2:
        level_patch_size = int(patch_size/slide.level_downsamples[slide_level])
        x_ws = (np.round(x_l*slide.level_downsamples[slide_level])).astype(int)
        y_ws = (np.round(y_l*slide.level_downsamples[slide_level])).astype(int)
        cnt=0

        while(len(patch_list) < patch_num) :
            # loop cnt
            cnt+=1
            #random Pick point in mask
            p_idx = randint(0,len(x_l)-1)
            #Get the point in mask
            level_point_x,level_point_y = x_l[p_idx], y_l[p_idx]
            #Check boundary to make patch
            check_bound = np.resize(np.array([level_point_x+level_patch_size,level_point_y+level_patch_size]),(2,))
            if check_bound[0] > mask.shape[0] or check_bound[1] > mask.shape[1]:
                continue
            #make patch from mask image
            level_patch_mask = mask[int(level_point_x):int(level_point_x+level_patch_size),int(level_point_y):int(level_point_y+level_patch_size)]

            '''Biggest difference is here'''
            #apply center window (32x32)
            cntr_x= (level_patch_size/2)-1
            cntr_y= (level_patch_size/2)-1

            win_x = cntr_x-window_size/2
            win_y = cntr_y-window_size/2

            t_window = level_patch_mask[win_x:(win_x+window_size),win_y:(win_y+window_size)]

            #apply integral to window
            ii_map = integral_image(t_window)
            ii_sum = integrate(ii_map,(0,0),(window_size-1,window_size-1))
            overlap = float(ii_sum)/(window_size**2)

            if overlap <1.0:
                continue

            if cnt > patch_num*10+1000:
                print "There is no moare patches to extract in this slide"
                print "mask region is too small"
                print "final number of patches : ",len(patch_list)

                break
            #patch,point is appended the list
            #print "region percent: ",overlap
            patch_point.append((x_l[p_idx],y_l[p_idx]))
            patch=slide.read_region((y_ws[p_idx],x_ws[p_idx]),0,(patch_size,patch_size))
            patch =np.array(patch)

            patch_list.append(cv2.cvtColor(patch,cv2.COLOR_RGBA2BGR))


    return patch_list, patch_point
