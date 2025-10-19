-- PostgreSQL script to create folder tables

-- Drop old folder table if it exists
DROP TABLE IF EXISTS folder CASCADE;

-- Create image_folders table
CREATE TABLE IF NOT EXISTS image_folders (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    display_order INTEGER DEFAULT 0 NOT NULL,
    is_deleted BOOLEAN DEFAULT FALSE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Create folder_images table
CREATE TABLE IF NOT EXISTS folder_images (
    id SERIAL PRIMARY KEY,
    folder_id INTEGER NOT NULL,
    image_id INTEGER NOT NULL,
    display_order INTEGER DEFAULT 0 NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    UNIQUE(folder_id, image_id),
    FOREIGN KEY (folder_id) REFERENCES image_folders(id) ON DELETE CASCADE,
    FOREIGN KEY (image_id) REFERENCES user_images(id) ON DELETE CASCADE
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_image_folders_user_id ON image_folders(user_id);
CREATE INDEX IF NOT EXISTS idx_image_folders_is_deleted ON image_folders(is_deleted);
CREATE INDEX IF NOT EXISTS idx_folder_images_folder_id ON folder_images(folder_id);
CREATE INDEX IF NOT EXISTS idx_folder_images_image_id ON folder_images(image_id);

-- Create function for auto-updating updated_at timestamp
CREATE OR REPLACE FUNCTION update_modified_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create triggers for updated_at timestamps
DROP TRIGGER IF EXISTS update_image_folders_modtime ON image_folders;
CREATE TRIGGER update_image_folders_modtime
BEFORE UPDATE ON image_folders
FOR EACH ROW
EXECUTE FUNCTION update_modified_column();

DROP TRIGGER IF EXISTS update_folder_images_modtime ON folder_images;
CREATE TRIGGER update_folder_images_modtime
BEFORE UPDATE ON folder_images
FOR EACH ROW
EXECUTE FUNCTION update_modified_column();

-- Verify tables were created
SELECT table_name FROM information_schema.tables WHERE table_name IN ('image_folders', 'folder_images'); 