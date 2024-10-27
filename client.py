import httpx
import traceback
import base64
from io import BytesIO
from PIL import Image

# URL of the FastAPI server
BASE_URL = "http://127.0.0.1:8000"  # Update this with the actual server URL


async def upload_image(file_path: str):
    """Uploads an image to the /transform endpoint and handles the response."""
    url = f"{BASE_URL}/transform"
    print(url)
    try:
        # Open the image file in binary mode
        with open(file_path, "rb") as image_file:
            files = {"file": (file_path, image_file, "image/jpeg")}

            # Send a POST request to the API
            async with httpx.AsyncClient(timeout=500) as client:
                response = await client.post(url, files=files)

            # Check the response status
            if response.status_code == 200:
                data = response.json()
                if data["success"]:
                    print("Image transformed successfully!")
                    print(f"Image URL: {data['image_url']}")
                    print(f"Description: {data['description']}")
                    image_data = base64.b64decode(data["image_bytes"])
                    image = Image.open(BytesIO(image_data))
                    image.show()
                else:
                    print(f"Transformation failed: {data['error']}")
            else:
                print(f"Error: Received status code {response.status_code}")

    except Exception as e:
        print(f"An error occurred: {e}")
        traceback.print_exc()


# Example usage
if __name__ == "__main__":
    import asyncio

    # Replace 'example.jpg' with the path to your image file
    asyncio.run(upload_image("chau-cay-tung-bong-lai-dia-lot-binh-hoa-1.jpg"))
