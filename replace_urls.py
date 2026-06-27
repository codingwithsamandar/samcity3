import os
import re

template_dir = r"c:\Users\user\Desktop\merged_project\main\templates"

REPLACEMENTS = [
    # Static paths
    (r'^/$', r"{% url 'home' %}"),
    (r'^/login/$', r"{% url 'login' %}"),
    (r'^/logout/$', r"{% url 'logout' %}"),
    (r'^/register/$', r"{% url 'register' %}"),
    
    # Profile
    (r'^/profile/$', r"{% url 'profile' %}"),
    (r'^/profile/edit/$', r"{% url 'profile_edit' %}"),
    (r'^/profile/update/$', r"{% url 'profile_update' %}"),
    (r'^/profile/delete/$', r"#"), # No corresponding URL, disable
    (r'^/profile/\{\{\s*([^}]+)\s*\}\}/$', r"{% url 'public_profile' \1 %}"),
    
    # General Ads
    (r'^/ads/$', r"{% url 'my_ads' %}"),
    (r'^/my-ads/$', r"{% url 'my_ads' %}"), # Corrected from my-ads which was broken
    (r'^/all-ads/$', r"{% url 'all_ads' %}"),
    (r'^/ads/new/$', r"{% url 'ad_create' %}"),
    (r'^/ads/\{\{\s*([^}]+)\s*\}\}/$', r"{% url 'ad_detail' \1 %}"),
    (r'^/ads/\{\{\s*([^}]+)\s*\}\}/edit/$', r"{% url 'ad_edit' \1 %}"),
    (r'^/ads/\{\{\s*([^}]+)\s*\}\}/delete/$', r"{% url 'ad_delete' \1 %}"),
    (r'^/ads/\{\{\s*([^}]+)\s*\}\}/mark-sold/$', r"{% url 'ad_toggle_sold' \1 %}"),
    (r'^/ads/\{\{\s*([^}]+)\s*\}\}/boost/$', r"{% url 'boost_ad' \1 %}"),
    
    # Bookings
    (r'^/bookings/$', r"{% url 'my_bookings' %}"),
    (r'^/my-bookings/$', r"{% url 'my_bookings' %}"),
    (r'^/received-bookings/$', r"{% url 'received_bookings' %}"),
    (r'^/bookings/\{\{\s*([^}]+)\s*\}\}/$', r"{% url 'booking_detail' \1 %}"),
    (r'^/bookings/\{\{\s*([^}]+)\s*\}\}/cancel/$', r"{% url 'booking_action' \1 'cancel' %}"),
    
    # Business
    (r'^/business/$', r"{% url 'business_list' %}"),
    (r'^/business/new/$', r"{% url 'business_create' %}"),
    (r'^/business/\{\{\s*([^}]+)\s*\}\}/$', r"{% url 'business_detail' \1 %}"),
    (r'^/business/\{\{\s*([^}]+)\s*\}\}/edit/$', r"{% url 'business_edit' \1 %}"),
    (r'^/business/\{\{\s*([^}]+)\s*\}\}/review/$', r"#"), # Check if review view exists
    
    # Transport
    (r'^/transport/$', r"{% url 'transport_list' %}"),
    (r'^/transport/add/$', r"{% url 'transport_create' %}"),
    (r'^/transport/\{\{\s*([^}]+)\s*\}\}/edit/$', r"{% url 'transport_edit' \1 %}"),
    
    # Courses
    (r'^/courses/$', r"{% url 'course_list' %}"),
    (r'^/courses/new/$', r"{% url 'course_create' %}"),
    (r'^/courses/\{\{\s*([^}]+)\s*\}\}/$', r"{% url 'course_detail' \1 %}"),
    (r'^/courses/\{\{\s*([^}]+)\s*\}\}/edit/$', r"{% url 'course_edit' \1 %}"),
    (r'^/courses/\{\{\s*([^}]+)\s*\}\}/delete/$', r"{% url 'course_delete' \1 %}"),
    
    # Jobs
    (r'^/jobs/$', r"{% url 'job_list' %}"),
    (r'^/jobs/new/$', r"{% url 'job_create' %}"),
    (r'^/jobs/\{\{\s*([^}]+)\s*\}\}/$', r"{% url 'job_detail' \1 %}"),
    (r'^/jobs/\{\{\s*([^}]+)\s*\}\}/edit/$', r"{% url 'job_edit' \1 %}"),
    (r'^/jobs/\{\{\s*([^}]+)\s*\}\}/delete/$', r"{% url 'job_delete' \1 %}"),
    
    # Resumes
    (r'^/resumes/$', r"{% url 'resume_list' %}"),
    (r'^/resumes/add/$', r"{% url 'resume_create' %}"),
    (r'^/resumes/\{\{\s*([^}]+)\s*\}\}/$', r"{% url 'resume_detail' \1 %}"),
    (r'^/resumes/\{\{\s*([^}]+)\s*\}\}/edit/$', r"{% url 'resume_edit' \1 %}"),
    (r'^/resumes/\{\{\s*([^}]+)\s*\}\}/delete/$', r"{% url 'resume_delete' \1 %}"),
    (r'^/resumes/\{\{\s*([^}]+)\s*\}\}/mark-hired/$', r"{% url 'resume_toggle_hired' \1 %}"),
    
    # Utilities
    (r'^/utilities/$', r"{% url 'utility_list' %}"),
    (r'^/utilities/add/$', r"{% url 'utility_create' %}"),
    (r'^/utilities/\{\{\s*([^}]+)\s*\}\}/edit/$', r"{% url 'utility_edit' \1 %}"),
    (r'^/utilities/\{\{\s*([^}]+)\s*\}\}/delete/$', r"{% url 'utility_delete' \1 %}"),
    
    # Chat
    (r'^/chat/$', r"{% url 'neighborhood_chat' %}"),
    (r'^/chat/\{\{\s*([^}]+)\s*\}\}/$', r"{% url 'neighborhood_chat_room' \1 %}"),
]

def replace_in_file(path):
    with open(path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    original_content = content
    
    # Regex to find href="/..." or action="/..."
    # We use a wrapper function to process the inner match
    def replacer(match):
        attr = match.group(1) # href or action
        url_val = "/" + match.group(2) # e.g. /profile/
        
        # We try to apply the REPLACEMENTS rules to url_val
        for pattern, replacement in REPLACEMENTS:
            if re.match(pattern, url_val):
                new_val = re.sub(pattern, replacement, url_val)
                return f'{attr}="{new_val}"'
        
        return match.group(0) # No change

    new_content = re.sub(r'(href|action)="/([^"]*)"', replacer, content)
    
    if new_content != original_content:
        with open(path, 'w', encoding='utf-8') as file:
            file.write(new_content)
        print(f"Updated: {path}")

for root, dirs, files in os.walk(template_dir):
    for f in files:
        if f.endswith('.html'):
            path = os.path.join(root, f)
            replace_in_file(path)

print("Done replacing.")
