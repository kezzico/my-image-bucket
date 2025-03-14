import boto3
from flask import Flask, jsonify, render_template, request
from dotenv import load_dotenv
import os
from PIL import Image
import io
app = Flask(__name__)
# Load environment variables from .env file
load_dotenv()

# Configure your Space
session = boto3.session.Session()
s3 = session.client(
    's3',
    region_name=os.getenv('REGION_NAME'),  # Replace with your region (e.g., sgp1, ams3)
    endpoint_url=os.getenv('ENDPOINT_URL'),  # Replace region in the URL
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
)

@app.route('/', methods=['GET'])
def home():
    return render_template('home.html')

@app.route('/files', methods=['GET'])
def list_files():
    space_name = os.getenv('SPACE_NAME')
    try:
        response = s3.list_objects_v2(Bucket=space_name)

        if 'Contents' in response:
            files = []
            sorted_contents = sorted(response['Contents'], key=lambda obj: obj['LastModified'], reverse=True)
            for obj in sorted_contents:
                file_url = f"https://sfo2.digitaloceanspaces.com/{space_name}/{obj['Key']}"
                files.append({
                    'key': obj['Key'],
                    'size': obj['Size'],
                    'url': file_url
                })
            return jsonify({'files': files})
        else:
            return jsonify({'message': f"No files found in '{space_name}'."}), 404

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/put', methods=['POST'])
def upload_file():
    space_name = 'kezzico-bucket'
    
    file = request.files['file']
    filename = request.form.get('name')

    if not filename:
        filename = file.filename

    try:
        image = Image.open(file)
        image_format = image.format

        file_extension = os.path.splitext(filename)[1].lower()
        print('file_extension', file_extension)

        if file_extension is None or file_extension == '':
            if image_format == 'JPEG':
                filename = filename + '.jpg'
            elif image_format == 'PNG':
                filename = filename + '.jpg'
            elif image_format == 'GIF':
                filename = filename + '.gif'
        
        if image_format == "PNG" and filename.lower().endswith('jpg'):
            print("converting png to jpg in progress")

            image = image.convert('RGB')
            buffer = io.BytesIO()
            image.save(buffer, format='JPEG')
            buffer.seek(0)
            file = buffer

            print('converted to jpg')
            
    except Exception as e:
        print('error converting', e)
        return jsonify({'error': str(e)}), 500

    print("preparing to upload", filename)
    try:
        s3.upload_fileobj(
            file, 
            space_name, 
            filename,
            ExtraArgs={'ContentType': 'image/jpeg' if image_format == 'JPEG' else 'image/png'}
        )
        s3.put_object_acl(ACL='public-read', Bucket=space_name, Key=filename)
        file_url = f"https://sfo2.digitaloceanspaces.com/{space_name}/{filename}"
        print('uploaded', file_url)
        return jsonify({'url': file_url}), 200
    except Exception as e:
        print('please fix this')
        print(e)
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
