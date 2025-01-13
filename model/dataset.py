import torch
from torch.utils.data import Dataset
from PIL import Image
import os

class CustomDataset(Dataset):
    def __init__(self, df, base_dir, metadata_type, transform=None):
        self.df = df
        self.base_dir = base_dir
        self.transform = transform
        self.metadata_type = metadata_type
        
        # Convert metadata to appropriate type
        self.df[metadata_type] = self.df[metadata_type].astype(int)
        self.df['covid_status'] = self.df['covid_status'].astype(int)

    def __len__(self):
        return len(self.df)

    def __getitem__(self, idx):
        img_file_name = self.df.iloc[idx]['img_file_name']
        img_path = os.path.join(self.base_dir, img_file_name)
        img = Image.open(img_path).convert('RGB')
        
        if self.transform:
            img = self.transform(img)
            
        metadata = self.df.iloc[idx][self.metadata_type]
        status = self.df.iloc[idx]['covid_status']
        
        return img, torch.tensor(metadata, dtype=torch.long), torch.tensor(status, dtype=torch.long)