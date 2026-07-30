class PaletteOperations:
    @staticmethod
    def get_palette_colors(image):
        """Returns a list of RGB tuples for the palette, or None if not indexed."""
        if image.mode != 'P':
            return None

        palette = image.getpalette()
        if not palette:
            return None

        colors = []
        for i in range(0, len(palette), 3):
            r, g, b = palette[i:i+3]
            colors.append((r, g, b))
        return colors

    @staticmethod
    def set_palette_colors(image, colors):
        """Sets the palette from a list of RGB tuples."""
        if image.mode != 'P':
            raise ValueError("Image must be in 'P' mode to set palette.")

        flat_palette = []
        for r, g, b in colors:
            flat_palette.extend([r, g, b])

        # Pad to 256 colors
        while len(flat_palette) < 768:
            flat_palette.append(0)

        image.putpalette(flat_palette[:768])

    @staticmethod
    def replace_index(image, old_index, new_index):
        """Replaces all occurrences of old_index with new_index in a 'P' mode image."""
        if image.mode != 'P':
            raise ValueError("Image must be in 'P' mode to replace index.")

        # Fast pixel replacement using point
        def map_index(idx):
            return new_index if idx == old_index else idx

        # apply point only updates image data, doesn't change mode or palette
        # but in Pillow, point for 'P' images returns a new image and can mess up palette
        # so we must restore the palette
        palette = image.getpalette()
        transparency = image.info.get('transparency', None)

        image.paste(image.point(map_index))
        image.putpalette(palette)
        if transparency is not None:
            image.info['transparency'] = transparency

    @staticmethod
    def replace_color(image, old_color, new_color):
        """
        Replaces all occurrences of old_color (R,G,B) with new_color (R,G,B) or (R,G,B,A).
        If 'P' mode, old_color must match a palette entry exactly, and it modifies the palette.
        If 'RGBA' or 'RGB' mode, it replaces pixel values directly.
        """
        if image.mode == 'P':
            colors = PaletteOperations.get_palette_colors(image)
            if not colors:
                return

            # Find the old color in the palette and change it
            for i, c in enumerate(colors):
                if c == old_color:
                    colors[i] = new_color

            PaletteOperations.set_palette_colors(image, colors)

        elif image.mode in ('RGBA', 'RGB'):
            # Load pixel data
            pixels = image.load()
            w, h = image.size
            for y in range(h):
                for x in range(w):
                    if pixels[x, y] == old_color:
                        pixels[x, y] = new_color
