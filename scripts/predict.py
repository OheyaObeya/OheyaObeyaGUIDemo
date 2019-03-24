import subprocess


def classify(image_path: str) -> dict:
    # curl -X POST -F image=@now.jpg 'http://localhost:5000/predict_3level'
    api_url = "http://localhost:5000/predict"
    command_format = "curl -X POST -F 'image=@{}' '{}'"
    p = command_format.format(image_path, api_url)
    result = subprocess.check_output(p, shell=True)
    text = result.decode('utf-8')
    text = text.replace('true', 'True')
    text = text.replace('false', 'False')
    result_dict = eval(text)
    return result_dict
