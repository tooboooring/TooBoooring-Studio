"""
Logo Creator for Video Production App

This script creates a simple logo for your Video Production App if you don't have one.
It creates a professional-looking logo with the app name and video-related icons.

Usage:
    python create_logo.py

This will create a logo.png file that can be used with your executable.
"""

from PIL import Image, ImageDraw, ImageFont
import os

def create_logo():
    """Create a professional logo for the Video Production App."""
    
    # Logo dimensions
    width, height = 256, 256
    
    # Create image with transparent background
    img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Define colors (matching your app theme)
    primary_color = (59, 130, 246)  # Blue
    secondary_color = (47, 179, 68)  # Green
    accent_color = (245, 158, 11)   # Amber
    text_color = (255, 255, 255)    # White
    
    # Draw background circle
    margin = 20
    draw.ellipse([margin, margin, width-margin, height-margin], 
                 fill=primary_color, outline=secondary_color, width=4)
    
    # Draw video camera icon (simplified)
    camera_x, camera_y = width // 2, height // 2 - 20
    
    # Camera body
    draw.rectangle([camera_x - 30, camera_y - 15, camera_x + 30, camera_y + 15], 
                  fill=text_color, outline=primary_color, width=2)
    
    # Camera lens
    draw.ellipse([camera_x - 20, camera_y - 10, camera_x + 20, camera_y + 10], 
                 fill=accent_color, outline=text_color, width=2)
    
    # Camera lens center
    draw.ellipse([camera_x - 8, camera_y - 4, camera_x + 8, camera_y + 4], 
                 fill=text_color)
    
    # Add app name
    try:
        # Try to use a system font
        font_large = ImageFont.truetype("arial.ttf", 24)
        font_small = ImageFont.truetype("arial.ttf", 14)
    except:
        # Fallback to default font
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    # App name
    app_name = "Video Production"
    version = "v3.0"
    
    # Get text dimensions for centering
    bbox_large = draw.textbbox((0, 0), app_name, font=font_large)
    text_width_large = bbox_large[2] - bbox_large[0]
    text_x_large = (width - text_width_large) // 2
    
    bbox_small = draw.textbbox((0, 0), version, font=font_small)
    text_width_small = bbox_small[2] - bbox_small[0]
    text_x_small = (width - text_width_small) // 2
    
    # Draw text
    draw.text((text_x_large, camera_y + 40), app_name, 
              fill=text_color, font=font_large)
    draw.text((text_x_small, camera_y + 65), version, 
              fill=accent_color, font=font_small)
    
    # Add some decorative elements
    # Small circles around the main circle
    for i in range(8):
        angle = i * 45
        import math
        x = width // 2 + 80 * math.cos(math.radians(angle))
        y = height // 2 + 80 * math.sin(math.radians(angle))
        draw.ellipse([x - 3, y - 3, x + 3, y + 3], fill=accent_color)
    
    # Save the logo
    img.save('logo.png', 'PNG')
    print("✅ Created logo.png successfully!")
    print("📁 Logo saved as: logo.png")
    print("🎨 Logo features:")
    print("   - Professional blue/green color scheme")
    print("   - Video camera icon")
    print("   - App name and version")
    print("   - Decorative elements")
    print("   - 256x256 pixels (high resolution)")
    
    return True

def main():
    """Main function to create the logo."""
    print("🎨 Creating logo for Video Production App...")
    print("=" * 50)
    
    try:
        if create_logo():
            print("=" * 50)
            print("🎉 Logo creation completed!")
            print("📁 Your logo is ready: logo.png")
            print("")
            print("🚀 Next steps:")
            print("   1. The logo will be automatically included in your executable")
            print("   2. Run: python build_app.py")
            print("   3. Your .exe will have the logo as its icon!")
            print("")
            print("💡 You can also replace logo.png with your own custom logo")
            print("   (recommended size: 256x256 pixels, PNG format)")
            
        return True
        
    except Exception as e:
        print(f"❌ Error creating logo: {e}")
        return False

if __name__ == "__main__":
    success = main()
    if not success:
        exit(1)
