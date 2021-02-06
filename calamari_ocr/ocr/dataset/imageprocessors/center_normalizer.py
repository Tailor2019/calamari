import numpy as np
from scipy.ndimage import filters
from calamari_ocr.ocr.dataset.imageprocessors.data_preprocessor import ImageProcessor
from calamari_ocr.ocr.dataset.imageprocessors.scale_to_height_processor import ScaleToHeightProcessor


class CenterNormalizer(ImageProcessor):
    @staticmethod
    def default_params() -> dict:
        return {
            'extra_params': (4, 1.0, 0.3),
        }

    def __init__(self, extra_params=(4, 1.0, 0.3), debug=False, **kwargs):
        super().__init__(**kwargs)
        self.debug = debug
        self.target_height = self.params.line_height_
        self.range, self.smoothness, self.extra = extra_params

    def _apply_single(self, data, meta):
        data = data / 255.0
        cval = np.amax(data) if data.size > 0 else 1
        out, params = self.normalize(data, cval=cval)
        meta['center'] = params
        return (out * 255).astype('uint8')

    def set_height(self, target_height):
        self.target_height = target_height

    def measure(self, line):
        h, w = line.shape
        smoothed = filters.gaussian_filter(line, (h * 0.5, h * self.smoothness), mode='constant')
        smoothed += 0.001 * filters.uniform_filter(smoothed, (h * 0.5, w), mode='constant')
        a = np.argmax(smoothed, axis=0)
        a = filters.gaussian_filter(a, h * self.extra)
        center = np.array(a, 'i')
        deltas = abs(np.arange(h)[:, np.newaxis] - center[np.newaxis, :])
        mad = np.mean(deltas[line != 0])
        r = int(1 + self.range * mad)

        return center, r

    def dewarp(self, img, cval=0, dtype=np.dtype('f')):
        if img.size == 0:
            # empty image
            return img

        temp = np.amax(img) - img
        amax = np.amax(temp)
        if amax == 0:
            # white image
            return temp

        temp = temp * 1.0 / np.amax(temp)
        center, r = self.measure(temp)
        h, w = img.shape
        # The actual image img is embedded into a larger image by
        # adding vertical space on top and at the bottom (padding)
        hpadding = r # this is large enough
        padded = np.vstack([cval * np.ones((hpadding, w)), img, cval * np.ones((hpadding, w))])
        center = center + hpadding
        dewarped = [padded[center[i] - r:center[i]+r, i] for i in range(w)]
        dewarped = np.array(dewarped, dtype=dtype).T

        return dewarped

    def normalize(self, img, order=1, dtype=np.dtype('f'), cval=0):
        # resize the image to a appropriate height close to the target height to speed up dewarping
        intermediate_height = int(self.target_height * 1.5)
        m1 = 1
        if intermediate_height < img.shape[0]:
            m1 = intermediate_height / img.shape[0]
            img = ScaleToHeightProcessor.scale_to_h(img, intermediate_height, order=order, dtype=dtype, cval=cval)

        # dewarp
        dewarped = self.dewarp(img, cval=cval, dtype=dtype)

        t = dewarped.shape[0] - img.shape[0]
        # scale to target height
        scaled = ScaleToHeightProcessor.scale_to_h(dewarped, self.target_height, order=order, dtype=dtype, cval=cval)
        if dewarped.shape[1] != 0:
            m2 = scaled.shape[1] / dewarped.shape[1]
        else:
            m2 = -1
        return scaled, (m1, m2, t)

    def local_to_global_pos(self, x, params):
        m1, m2, t = params['center']
        return x / m1 / m2

