import json
import boto3
import csv
import io
from datetime import datetime
import traceback

s3_client = boto3.client('s3')

def lambda_handler(event, context):
    print("=" * 50)
    print("DEBUG: Lambda function STARTED")
    print("=" * 50)
    
    try:
        bucket = event['Records'][0]['s3']['bucket']['name']
        key = event['Records'][0]['s3']['object']['key']
        
        print(f"Processing: {key} from {bucket}")
        
        response = s3_client.get_object(Bucket=bucket, Key=key)
        content = response['Body'].read().decode('utf-8')
        
        reader = csv.reader(io.StringIO(content))
        rows = list(reader)
        
        if not rows:
            raise ValueError("CSV file is empty")
            
        header = rows[0]
        data = rows[1:]
        
        print(f"Original rows: {len(data)}")
        
        unique_data = []
        seen = set()
        duplicates = 0
        
        for row in data:
            row_tuple = tuple(row)
            if row_tuple not in seen:
                seen.add(row_tuple)
                unique_data.append(row)
            else:
                duplicates += 1
        
        print(f"Removed {duplicates} duplicate rows")
        
        header.extend(['processed_date', 'source_file', 'row_number'])
        
        output_rows = [header]
        for i, row in enumerate(unique_data):
            output_rows.append(row + [
                datetime.now().isoformat(),
                key,
                str(i + 1)
            ])
        
        output_bucket = 'ash-processed-date-2026'
        original_filename = key.split('/')[-1]
        output_key = f"cleaned/{original_filename.replace('.csv', '_cleaned.csv')}"
        
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerows(output_rows)
        
        s3_client.put_object(
            Bucket=output_bucket,
            Key=output_key,
            Body=output.getvalue(),
            ContentType='text/csv'
        )
        
        print(f"✅ SUCCESS: Saved {len(unique_data)} rows to s3://{output_bucket}/{output_key}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Success!',
                'original_rows': len(data),
                'cleaned_rows': len(unique_data),
                'duplicates_removed': duplicates,
                'output_location': f"s3://{output_bucket}/{output_key}"
            })
        }
        
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        print(traceback.format_exc())
        raise e