from datetime import datetime
from pathlib import Path

import cv2
from pypylon import pylon

import basler_camera


FOLDER = Path(__file__).resolve().parent / "zdjecia"
JPG_QUALITY = 95


def save_jpg(frame):
    FOLDER.mkdir(exist_ok=True)
    filename = FOLDER / f"snap_{datetime.now():%Y%m%d_%H%M%S_%f}.jpg"

    if not cv2.imwrite(str(filename), frame, [cv2.IMWRITE_JPEG_QUALITY, JPG_QUALITY]):
        raise RuntimeError(f"Nie udało się zapisać {filename}")

    print("Zapisano zdjęcie:", filename)


def main():
    camera = basler_camera.open_camera()

    try:
        converter = basler_camera.make_converter(camera)

        # zawsze najnowsza klatka - podglad nie zostaje w tyle
        camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
        print("Podgląd: s - zapisz JPG, q - zakończ")

        while camera.IsGrabbing():
            with camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException) as result:
                if not result.GrabSucceeded():
                    print(f"Pominięta klatka: {result.ErrorCode} {result.ErrorDescription}")
                    continue

                frame = converter.Convert(result).GetArray()

            cv2.imshow("Basler", frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("s"):
                save_jpg(frame)
            elif key == ord("q"):
                break

            # zamkniecie okna krzyzykiem
            if cv2.getWindowProperty("Basler", cv2.WND_PROP_VISIBLE) < 1:
                break

    finally:
        camera.StopGrabbing()
        camera.Close()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
