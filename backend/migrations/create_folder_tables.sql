-- SQL script to create folder tables

-- Create image_folders table
CREATE TABLE IF NOT EXISTS image_folders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    display_order INTEGER DEFAULT 0 NOT NULL,
    is_deleted BOOLEAN DEFAULT 0 NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Create folder_images table
CREATE TABLE IF NOT EXISTS folder_images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
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

-- Verify tables were created
SELECT 'Tables created successfully' AS message;
SELECT name FROM sqlite_master WHERE type='table' AND (name='image_folders' OR name='folder_images'); 