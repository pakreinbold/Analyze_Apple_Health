import zipfile

zip_path = '/Users/patri/Downloads/export.zip'
unzip_path = '/Users/patri/Documents/GitHub/Analyze_Apple_Health/'  # noqa
with zipfile.ZipFile(zip_path, 'r') as zip_ref:
    zip_ref.extractall(unzip_path)
