# -*- coding: utf-8 -*-
import subprocess
import os
import uuid 
import tempfile
import traceback # Import traceback for detailed error logging

# Asumiendo que convert.exe está en el mismo directorio que composite.exe
IMAGEMAGICK_DIR = r"C:\Telltale\ArtData\Tools\Maya\Apps\ImageMagick" 
IMAGEMAGICK_CONVERT_EXE = os.path.join(IMAGEMAGICK_DIR, "convert.exe")
IMAGEMAGICK_COMPOSITE_EXE = os.path.join(IMAGEMAGICK_DIR, "composite.exe")

# Parámetros para la visualización (se usan en enhance_uv_snapshot)
LINE_DILATION_RADIUS = "1.5" 
SHELL_FILL_COLOR = "rgba(128,128,128,0.4)" 

def enhance_uv_snapshot(input_uv_png_path, output_enhanced_png_path):
    """
    Enhances a basic UV snapshot PNG with thicker lines and filled shells using ImageMagick.

    :param input_uv_png_path: Path to the original thin-line UV PNG file.
    :param output_enhanced_png_path: Path where the enhanced PNG will be saved.
    :return: True if successful, False otherwise.
    """
    if not os.path.isfile(IMAGEMAGICK_CONVERT_EXE):
        print("[ERROR] ImageMagick convert.exe not found at: {}".format(IMAGEMAGICK_CONVERT_EXE))
        return False
    if not os.path.isfile(input_uv_png_path):
        print("[ERROR] Input UV snapshot image not found: {}".format(input_uv_png_path))
        return False

    # Generar nombres únicos para archivos temporales
    temp_id = uuid.uuid4().hex
    temp_dir = tempfile.gettempdir()
    
    # Archivos intermedios
    mask_path = os.path.join(temp_dir, "mask_{}.png".format(temp_id))
    inverted_mask_path = os.path.join(temp_dir, "inv_mask_{}.png".format(temp_id))
    filled_outside_mask_path = os.path.join(temp_dir, "fill_mask_{}.png".format(temp_id))
    shell_fill_layer_path = os.path.join(temp_dir, "shells_{}.png".format(temp_id))
    thick_line_layer_path = os.path.join(temp_dir, "lines_{}.png".format(temp_id))

    temp_files = [mask_path, inverted_mask_path, filled_outside_mask_path, 
                  shell_fill_layer_path, thick_line_layer_path]

    try:
        print("[INFO] Starting UV enhancement for: {}".format(input_uv_png_path))
        print("[INFO]   Outputting enhanced UV to: {}".format(output_enhanced_png_path))

        # --- Paso 1: Crear capa de relleno de Shells ---
        cmd_mask = [IMAGEMAGICK_CONVERT_EXE, input_uv_png_path, "-alpha", "extract", mask_path]
        subprocess.check_call(cmd_mask)
        cmd_invert = [IMAGEMAGICK_CONVERT_EXE, mask_path, "-negate", inverted_mask_path]
        subprocess.check_call(cmd_invert)
        cmd_fill_outside = [
            IMAGEMAGICK_CONVERT_EXE, inverted_mask_path,
            "-fill", "black", "-bordercolor", "white", "-border", "1x1", 
            "-draw", "color 0,0 floodfill", 
            "-shave", "1x1", 
            filled_outside_mask_path
        ]
        subprocess.check_call(cmd_fill_outside)
        cmd_shell_layer = [
            IMAGEMAGICK_CONVERT_EXE, filled_outside_mask_path,
            "-fill", SHELL_FILL_COLOR, "-opaque", "white", 
            "-fill", "transparent", "-opaque", "black",    
            shell_fill_layer_path
        ]
        subprocess.check_call(cmd_shell_layer)
        # print("[DEBUG] Shell fill layer created: {}".format(shell_fill_layer_path)) # Optional debug

        # --- Paso 2: Crear capa de líneas gruesas ---
        cmd_thicken = [
            IMAGEMAGICK_CONVERT_EXE, input_uv_png_path,
            "-morphology", "Dilate", "Disk:{}".format(LINE_DILATION_RADIUS), 
            thick_line_layer_path
        ]
        subprocess.check_call(cmd_thicken)
        # print("[DEBUG] Thick line layer created: {}".format(thick_line_layer_path)) # Optional debug

        # --- Paso 3: Combinar Shells y Líneas Gruesas (guardar como salida final) ---
        cmd_combine_uv = [
            IMAGEMAGICK_CONVERT_EXE, shell_fill_layer_path, thick_line_layer_path,
            "-compose", "over", 
            "-composite",
            output_enhanced_png_path # Guardar directamente en la ruta de salida deseada
        ]
        subprocess.check_call(cmd_combine_uv)
        
        # Verificar que el archivo se creó
        if os.path.exists(output_enhanced_png_path):
             print("[SUCCESS] Enhanced UV image saved: {}".format(output_enhanced_png_path))
             return True
        else:
             print("[ERROR] Enhancement command ran but output file was not created: {}".format(output_enhanced_png_path))
             return False

    except Exception as e:
        print("\n" + "="*20 + " UV ENHANCEMENT ERROR " + "="*20)
        print("[ERROR] Failed during ImageMagick UV enhancement.")
        print("        Input UV: {}".format(input_uv_png_path))
        print("        Output: {}".format(output_enhanced_png_path))
        print("        Error: {}".format(str(e)))
        print("        Traceback:")
        print(traceback.format_exc())
        print("="*60 + "\n")
        return False

    finally:
        # Limpieza de archivos temporales de mejora
        # print("[DEBUG] Cleaning up enhancement temporary files...")
        for temp_file in temp_files:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception as e:
                    print("[WARNING] Failed to remove enhancement temporary file '{}': {}".format(temp_file, e))

def compose_uv_over_texture(enhanced_uv_png_path, texture_image_path, output_composed_jpg_path, uv_width, uv_height):
    """
    Composes an ENHANCED UV snapshot (PNG with transparency) over a texture 
    and saves the result as a JPEG.

    :param enhanced_uv_png_path: Path to the ENHANCED UV PNG file (thick lines, shells).
    :param texture_image_path: Path to the texture image.
    :param output_composed_jpg_path: Path to the final composed output JPEG.
    :param uv_width: Width of the UV snapshot (used for resizing texture).
    :param uv_height: Height of the UV snapshot (used for resizing texture).
    :return: True if successful, False otherwise.
    """
    if not os.path.isfile(IMAGEMAGICK_CONVERT_EXE):
        print("[ERROR] ImageMagick convert.exe not found at: {}".format(IMAGEMAGICK_CONVERT_EXE))
        return False
    if not os.path.isfile(IMAGEMAGICK_COMPOSITE_EXE):
        print("[ERROR] ImageMagick composite.exe not found at: {}".format(IMAGEMAGICK_COMPOSITE_EXE))
        return False
        
    if not os.path.isfile(enhanced_uv_png_path):
        print("[ERROR] Input ENHANCED UV image not found: {}".format(enhanced_uv_png_path))
        return False
    if not os.path.isfile(texture_image_path):
        print("[ERROR] Input texture image not found: {}".format(texture_image_path))
        return False

    # Generar nombre único para la textura redimensionada
    temp_id = uuid.uuid4().hex
    temp_dir = tempfile.gettempdir()
    resized_texture_path = os.path.join(temp_dir, "resized_texture_{}.png".format(temp_id))
    
    try:
        # --- Paso 1: Redimensionar la Textura Base ---
        print("[INFO] Resizing base texture for composition...")
        resize_cmd = [
            IMAGEMAGICK_CONVERT_EXE, 
            texture_image_path,
            "-resize", "{}x{}!".format(uv_width, uv_height), 
            "-alpha", "off", 
            resized_texture_path
        ]
        subprocess.check_call(resize_cmd)
        print("[INFO] Resized texture saved: {}".format(resized_texture_path))

        # --- Paso 2: Componer UV Mejorado sobre Textura Redimensionada ---
        print("[INFO] Compositing enhanced UV over texture...")
        command = [
            IMAGEMAGICK_COMPOSITE_EXE,
            "-compose", "over",      
            "-gravity", "center",    
            enhanced_uv_png_path,        # ENHANCED UV PNG
            resized_texture_path,        # Resized texture
            "-quality", "95",       
            output_composed_jpg_path     # Salida final JPEG
        ]
        subprocess.check_call(command)
        
        if os.path.exists(output_composed_jpg_path):
            print("[SUCCESS] Composition successful. Saved: {}".format(output_composed_jpg_path))
            return True
        else:
            print("[ERROR] Composition command ran but output file was not created: {}".format(output_composed_jpg_path))
            return False

    except Exception as e:
        print("\n" + "="*20 + " IMAGE COMPOSITION ERROR " + "="*20)
        print("[ERROR] Failed during ImageMagick composition.")
        print("        Enhanced UV: {}".format(enhanced_uv_png_path))
        print("        Texture: {}".format(texture_image_path))
        print("        Output: {}".format(output_composed_jpg_path))
        print("        Error: {}".format(str(e)))
        print("        Traceback:")
        print(traceback.format_exc())
        print("="*60 + "\n")
        return False
        
    finally:
        # Limpieza archivo temporal de textura
        if os.path.exists(resized_texture_path):
            try:
                os.remove(resized_texture_path)
            except Exception as e:
                print("[WARNING] Failed to remove resized texture temporary file '{}': {}".format(resized_texture_path, e))