import cv2
import mediapipe as mp
import numpy as np
import screen_brightness_control as sbc
from collections import deque

# Initialize Mediapipe Hand Detection
mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils
hands = mp_hands.Hands(min_detection_confidence=0.7, min_tracking_confidence=0.7)

# Initialize Camera and Canvas
cap = cv2.VideoCapture(0)
canvas = np.zeros((480, 640, 3), dtype=np.uint8)  # Blank canvas for drawing

# Variables for left-hand shake detection
left_hand_positions = deque(maxlen=10)
shake_threshold = 50

# Variables for right-hand drawing
previous_point = None

# Text tracking
written_text = ""

# Main Loop
while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        print("Failed to capture video. Exiting...")
        break

    # Flip and convert frame for processing
    frame = cv2.flip(frame, 1)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # Perform hand detection
    result = hands.process(rgb_frame)
    right_hand_present = False
    left_hand_present = False

    if result.multi_hand_landmarks:
        for idx, hand_landmarks in enumerate(result.multi_hand_landmarks):
            # Determine if the hand is right or left
            handedness = result.multi_handedness[idx].classification[0].label
            if handedness == "Right":
                right_hand_present = True
            elif handedness == "Left":
                left_hand_present = True

            # Draw landmarks
            mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

            # Get coordinates of key landmarks
            h, w, _ = frame.shape
            thumb_tip = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP]
            index_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]

            thumb_coords = (int(thumb_tip.x * w), int(thumb_tip.y * h))
            index_coords = (int(index_tip.x * w), int(index_tip.y * h))

            if handedness == "Right":
                # Draw on canvas using the movement of the index finger
                if previous_point is None:
                    previous_point = index_coords
                else:
                    cv2.line(canvas, previous_point, index_coords, (255, 255, 255), 5)
                    previous_point = index_coords

                # Recognize writing (simple placeholder, needs actual OCR for letters)
                cv2.putText(frame, "Drawing...", (10, 100),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

            if handedness == "Left":
                # Brightness Control
                distance = np.linalg.norm(np.array(thumb_coords) - np.array(index_coords))
                brightness = np.interp(distance, [50, 200], [0, 100])
                try:
                    sbc.set_brightness(int(brightness))  # Set brightness level
                except Exception as e:
                    print(f"Could not set brightness: {e}")

                # Display brightness on screen
                cv2.putText(frame, f'Brightness: {int(brightness)}%', (10, 50),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

                # Shake Detection for Erase
                palm_coords = hand_landmarks.landmark[mp_hands.HandLandmark.WRIST]
                palm_point = (int(palm_coords.x * w), int(palm_coords.y * h))
                left_hand_positions.append(palm_point)

                if len(left_hand_positions) == left_hand_positions.maxlen:
                    movement = sum(
                        np.linalg.norm(np.array(left_hand_positions[i]) - np.array(left_hand_positions[i - 1]))
                        for i in range(1, len(left_hand_positions))
                    )
                    if movement > shake_threshold:
                        canvas = np.zeros((480, 640, 3), dtype=np.uint8)  # Clear canvas
                        previous_point = None  # Reset drawing point

    else:
        previous_point = None  # Reset if no hand is detected

    # Combine frame and canvas
    combined = cv2.addWeighted(frame, 0.5, canvas, 0.5, 0)

    # Display output
    cv2.imshow("Hand Gesture Control", combined)

    # Break loop on 'q' key press
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release resources
cap.release()
cv2.destroyAllWindows()
