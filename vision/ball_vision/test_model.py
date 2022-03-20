import collections
import cv2
import numpy as np
import tensorflow as tf



class BBox(collections.namedtuple('BBox', ['xmin', 'ymin', 'xmax', 'ymax'])):
    """Bounding box.
    Represents a rectangle which sides are either vertical or horizontal, parallel
    to the x or y axis.
    """
    __slots__ = ()

    def scale(self, sx, sy):
        """Returns scaled bounding box."""
        return BBox(xmin=sx * self.xmin,
                    ymin=sy * self.ymin,
                    xmax=sx * self.xmax,
                    ymax=sy * self.ymax)


class Tester:
    def __init__(self):
        try:
            model_path = "output_tflite_graph_edgetpu.tflite"
            self.interpreter = tf.lite.Interpreter(model_path, experimental_delegates=[tf.lite.experimental.load_delegate('libedgetpu.so.1')])
            self.hardware_type = "Coral Edge TPU"
        except Exception as e:
            print(e)
            print("Failed to create Interpreter with Coral, switching to unoptimized")
            model_path = "output_tflite_graph.tflite"
            self.interpreter = tf.lite.Interpreter(model_path)
            self.hardware_type = "Unoptimized"

        self.interpreter.allocate_tensors()

        self.labels = ["Red", "Blue"]
        self.temp_entry = []


    def check_box(self, box):
        width = box[2] - box[0]
        height = box[3] - box[1]
        return height != 0 and abs(1 - width / height) <= 0.3


    def run(self):
        while True:
            frame = cv2.imread("../test_image.png")
            if True:
                scale = self.set_input(frame)
                self.interpreter.invoke()
                boxes, class_ids, scores, _, _ = self.get_output(scale)
                width, height = self.input_size()
                resized = cv2.resize(frame, (width, height))

                for i, box in enumerate(boxes):
                    if scores[i] > 0.4 and self.check_box(box):
                        class_id = class_ids[i]
                        
                        if np.isnan(class_id):
                            continue

                        class_id = int(class_id)
                        if class_id not in range(len(self.labels)):
                            continue
                        
                        color = (0, 0, 255)

                        resized = self.label_frame(resized, self.labels[class_id], box, scores[i], width,
                                                        height, color)


                cv2.imshow("Output", resized)

                if cv2.waitKey(25) & 0xFF == ord('q'):
                    break
            else:
                break
        cap.release()
        cv2.destroyAllWindows()

    
    def input_size(self):
        """Returns input image size as (width, height) tuple."""
        _, height, width, _ = self.interpreter.get_input_details()[0]['shape']
        return width, height


    def set_input(self, frame):
        """Copies a resized and properly zero-padded image to the input tensor.
        Args:
          frame: image
        Returns:
          Actual resize ratio, which should be passed to `get_output` function.
        """
        width, height = self.input_size()
        h, w, _ = frame.shape
        new_img = np.reshape(cv2.resize(frame, (width, height)), (1, width, height, 3))
        self.interpreter.set_tensor(self.interpreter.get_input_details()[0]['index'], np.copy(new_img))
        return width / w, height / h

    
    def output_tensor(self, i):
        tensor = self.interpreter.get_tensor(self.interpreter.get_output_details()[i]['index'])
        return np.squeeze(tensor)


    def get_output(self, scale):
        boxes = self.output_tensor(1)
        class_ids = self.output_tensor(3)
        scores = self.output_tensor(0)

        width, height = self.input_size()
        image_scale_x, image_scale_y = scale
        x_scale, y_scale = width / image_scale_x, height / image_scale_y
        return boxes, class_ids, scores, x_scale, y_scale

    
    def label_frame(self, frame, object_name, box, score, x_scale, y_scale, color):
        ymin, xmin, ymax, xmax = box
        score = float(score)
        bbox = BBox(xmin=xmin,
                    ymin=ymin,
                    xmax=xmax,
                    ymax=ymax).scale(x_scale, y_scale)

        height, width, channels = frame.shape
        # check bbox validity
        if not 0 <= ymin < ymax <= height or not 0 <= xmin < xmax <= width:
            return frame

        ymin, xmin, ymax, xmax = int(bbox.ymin), int(bbox.xmin), int(bbox.ymax), int(bbox.xmax)
        self.temp_entry.append({"label": object_name, "box": {"ymin": ymin, "xmin": xmin, "ymax": ymax, "xmax": xmax},
                                "confidence": score})

        cv2.rectangle(frame, (xmin, ymin), (xmax, ymax), (10, 255, 0), 4)

        # Draw label
        # Look up object name from "labels" array using class index
        label = '%s: %d%%' % (object_name, score * 100)  # Example: 'person: 72%'
        label_size, base = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)  # Get font size
        label_ymin = max(ymin, label_size[1] + 10)  # Make sure not to draw label too close to top of window
        cv2.rectangle(frame, (xmin, label_ymin - label_size[1] - 10), (xmin + label_size[0], label_ymin + base - 10),
                      color, cv2.FILLED)
        # Draw label text
        cv2.putText(frame, label, (xmin, label_ymin - 7), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
        return frame


if __name__ == "__main__":
    tester = Tester()
    tester.run()