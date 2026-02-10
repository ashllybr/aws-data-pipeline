import json
import boto3
import pandas as pd
import io
from datetime import datetime

s3_client = boto3.client('s3')
sns_client = boto3.client('sns')

# Configuration
SNS_TOPIC_ARN = None  # Set this if you want email alerts
COST_PER_INVOCATION = 0.0000002  # $0.20 per 1M requests
COST_PER_GB_SECOND = 0.0000166667  # Lambda pricing

def lambda_handler(event, context):
    """
    COVID-19 Data Processing Pipeline
    
    Processes COVID-19 data from Our World in Data:
    - Filters for specific countries
    - Calculates daily change metrics
    - Identifies data quality issues
    - Generates summary statistics
    - Sends alerts on anomalies
    """
    
    start_time = datetime.now()
    
    try:
        # Get file information
        bucket = event['Records'][0]['s3']['bucket']['name']
        key = event['Records'][0]['s3']['object']['key']
        
        print(f"📊 Processing COVID-19 data: {key}")
        
        # Read CSV from S3
        response = s3_client.get_object(Bucket=bucket, Key=key)
        df = pd.read_csv(io.BytesIO(response['Body'].read()))
        
        print(f"📈 Original dataset: {df.shape[0]:,} rows, {df.shape[1]} columns")
        
        # DATA QUALITY CHECKS
        print("🔍 Running data quality checks...")
        
        # Remove duplicates
        original_count = len(df)
        df = df.drop_duplicates(subset=['location', 'date'])
        duplicates_removed = original_count - len(df)
        
        # Filter for specific countries (reduce dataset size)
        countries_of_interest = ['South Africa', 'United States', 'United Kingdom', 
                                'Germany', 'France', 'India', 'Brazil', 'Kenya']
        df_filtered = df[df['location'].isin(countries_of_interest)].copy()
        
        print(f"🌍 Filtered to {len(countries_of_interest)} countries: {len(df_filtered):,} rows")
        
        # DATA ENRICHMENT
        print("💡 Enriching data with calculated metrics...")
        
        # Convert date to datetime
        df_filtered['date'] = pd.to_datetime(df_filtered['date'])
        
        # Calculate daily changes
        df_filtered = df_filtered.sort_values(['location', 'date'])
        df_filtered['new_cases_7day_avg'] = df_filtered.groupby('location')['new_cases'].transform(
            lambda x: x.rolling(7, min_periods=1).mean()
        )
        
        # Add processing metadata
        df_filtered['processed_timestamp'] = datetime.now().isoformat()
        df_filtered['data_quality_score'] = df_filtered.apply(calculate_quality_score, axis=1)
        
        # SUMMARY STATISTICS
        summary = generate_summary(df_filtered, countries_of_interest)
        
        # SAVE PROCESSED DATA
        output_bucket = 'ash-processed-date-2026'
        output_key = f"cleaned/covid-analysis-{datetime.now().strftime('%Y%m%d')}.csv"
        
        csv_buffer = io.StringIO()
        df_filtered.to_csv(csv_buffer, index=False)
        
        s3_client.put_object(
            Bucket=output_bucket,
            Key=output_key,
            Body=csv_buffer.getvalue(),
            Metadata={
                'original-rows': str(original_count),
                'processed-rows': str(len(df_filtered)),
                'countries': str(len(countries_of_interest))
            }
        )
        
        # CALCULATE COSTS
        end_time = datetime.now()
        duration_seconds = (end_time - start_time).total_seconds()
        memory_gb = 0.5  # 512 MB = 0.5 GB
        
        cost_estimate = {
            'invocation_cost': COST_PER_INVOCATION,
            'compute_cost': duration_seconds * memory_gb * COST_PER_GB_SECOND,
            'total_cost': COST_PER_INVOCATION + (duration_seconds * memory_gb * COST_PER_GB_SECOND)
        }
        
        # SEND ALERT IF ANOMALIES DETECTED
        if summary.get('anomalies_detected', 0) > 0:
            send_alert(summary, SNS_TOPIC_ARN)
        
        print(f"✅ Processing complete!")
        print(f"📊 Summary: {json.dumps(summary, indent=2)}")
        print(f"💰 Cost: ${cost_estimate['total_cost']:.6f}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'COVID-19 data processed successfully',
                'original_rows': original_count,
                'processed_rows': len(df_filtered),
                'duplicates_removed': duplicates_removed,
                'countries_analyzed': len(countries_of_interest),
                'output_location': f"s3://{output_bucket}/{output_key}",
                'processing_time_seconds': duration_seconds,
                'estimated_cost_usd': cost_estimate['total_cost'],
                'summary': summary
            })
        }
        
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        
        # Send error alert
        if SNS_TOPIC_ARN:
            sns_client.publish(
                TopicArn=SNS_TOPIC_ARN,
                Subject='COVID-19 Pipeline Error',
                Message=f"Error processing data: {str(e)}"
            )
        
        raise e


def calculate_quality_score(row):
    """Calculate data quality score (0-100)"""
    score = 100
    
    # Deduct points for missing critical fields
    if pd.isna(row.get('total_cases')):
        score -= 20
    if pd.isna(row.get('new_cases')):
        score -= 15
    if pd.isna(row.get('total_deaths')):
        score -= 15
    
    # Deduct points for suspicious values
    if row.get('new_cases', 0) < 0:
        score -= 30
    if row.get('new_deaths', 0) < 0:
        score -= 30
    
    return max(0, score)


def generate_summary(df, countries):
    """Generate summary statistics"""
    summary = {
        'total_rows': len(df),
        'date_range': {
            'start': df['date'].min().strftime('%Y-%m-%d'),
            'end': df['date'].max().strftime('%Y-%m-%d')
        },
        'countries': countries,
        'total_cases': int(df['total_cases'].sum()) if 'total_cases' in df else 0,
        'total_deaths': int(df['total_deaths'].sum()) if 'total_deaths' in df else 0,
        'avg_quality_score': float(df['data_quality_score'].mean()),
        'low_quality_rows': int((df['data_quality_score'] < 70).sum()),
        'anomalies_detected': int((df['new_cases'] < 0).sum() + (df['new_deaths'] < 0).sum())
    }
    
    return summary


def send_alert(summary, topic_arn):
    """Send SNS alert for anomalies"""
    if not topic_arn:
        return
    
    message = f"""
    COVID-19 Data Pipeline Alert
    
    Anomalies detected: {summary['anomalies_detected']}
    Low quality rows: {summary['low_quality_rows']}
    Average quality score: {summary['avg_quality_score']:.1f}%
    
    Date range: {summary['date_range']['start']} to {summary['date_range']['end']}
    Total rows processed: {summary['total_rows']:,}
    """
    
    sns_client.publish(
        TopicArn=topic_arn,
        Subject='⚠️ COVID-19 Pipeline Alert',
        Message=message
    )