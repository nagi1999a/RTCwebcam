import numpy as np
class FlipPlugin:
    def process(self, frame):
        return np.flip(frame, axis=1)

class PortraitPaddingPlugin:
    def process(self, frame):
        if frame.shape[0] > frame.shape[1]:
            aspect_ratio = frame.shape[0] / frame.shape[1]
            padding_size = int(frame.shape[0]  * aspect_ratio - frame.shape[1]) // 2
            frame = np.pad(frame, ((0, 0), (padding_size, padding_size), (0, 0)), 'constant')
            return frame
        else:
            return frame