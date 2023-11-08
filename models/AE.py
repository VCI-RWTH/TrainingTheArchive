import torch.nn as nn
import torchvision.transforms as transforms


class ArtAE(nn.Module):
    def __init__(self, out_dim):
        super().__init__()
        self.out_dim = out_dim
        self.encoder = nn.Sequential(
            nn.Conv2d(3, 24, 5, bias=False, padding=2),
            nn.ReLU(),
            nn.BatchNorm2d(24),
            nn.MaxPool2d(2, 2),

            nn.Conv2d(24, 48, 5, bias=False, padding=2),
            nn.ReLU(),
            nn.BatchNorm2d(48),
            nn.MaxPool2d(2, 2),

            nn.Conv2d(48, 96, 5, bias=False, padding=2),
            nn.ReLU(),
            nn.BatchNorm2d(96),
            nn.MaxPool2d(2, 2),

            nn.Conv2d(96, 128, 5, bias=False, padding=2),
            nn.ReLU(),
            nn.BatchNorm2d(128),
            nn.MaxPool2d(2, 2),

            nn.Conv2d(128, 256, 3, bias=False, padding=1),
            nn.ReLU(),
            nn.BatchNorm2d(256),
            nn.MaxPool2d(2, 2),

            nn.Conv2d(256, 512, 3, bias=False, padding=1),
            nn.ReLU(),
            nn.BatchNorm2d(512),
            nn.MaxPool2d(2, 2),

            nn.Conv2d(512, 512, 3, bias=False, padding=1),
            nn.ReLU(),
            nn.BatchNorm2d(512),
            nn.MaxPool2d(2, 2),

            nn.Conv2d(512, 1024, 3, bias=False, padding=1),
            nn.ReLU(),
            nn.BatchNorm2d(1024),
            nn.MaxPool2d(2, 2),
        )

        self.decoder = nn.Sequential(
            nn.Upsample(scale_factor=2, mode='bilinear'),
            nn.Conv2d(1024, 512, 3, bias=False, padding=1),
            nn.ReLU(),
            nn.BatchNorm2d(512),

            nn.Upsample(scale_factor=2, mode='bilinear'),
            nn.Conv2d(512, 512, 3, bias=False, padding=1),
            nn.ReLU(),
            nn.BatchNorm2d(512),

            nn.Upsample(scale_factor=2, mode='bilinear'),
            nn.Conv2d(512, 256, 3, bias=False, padding=1),
            nn.ReLU(),
            nn.BatchNorm2d(256),
            nn.Conv2d(256, 256, 3, bias=False, padding=1),
            nn.ReLU(),
            nn.BatchNorm2d(256),

            nn.Upsample(scale_factor=2, mode='bilinear'),
            nn.Conv2d(256, 128, 3, bias=False, padding=1),
            nn.ReLU(),
            nn.BatchNorm2d(128),
            nn.Conv2d(128, 128, 3, bias=False, padding=1),
            nn.ReLU(),
            nn.BatchNorm2d(128),

            nn.Upsample(scale_factor=2, mode='bilinear'),
            nn.Conv2d(128, 96, 5, bias=False, padding=2),
            nn.ReLU(),
            nn.BatchNorm2d(96),
            nn.Conv2d(96, 96, 3, bias=False, padding=1),
            nn.ReLU(),
            nn.BatchNorm2d(96),

            nn.Upsample(scale_factor=2, mode='bilinear'),
            nn.Conv2d(96, 48, 5, bias=False, padding=2),
            nn.ReLU(),
            nn.BatchNorm2d(48),
            nn.Conv2d(48, 48, 3, bias=False, padding=1),
            nn.ReLU(),
            nn.BatchNorm2d(48),

            nn.Upsample(scale_factor=2, mode='bilinear'),
            nn.Conv2d(48, 24, 5, bias=False, padding=2),
            nn.ReLU(),
            nn.BatchNorm2d(24),
            nn.Conv2d(24, 24, 5, bias=False, padding=2),
            nn.ReLU(),
            nn.BatchNorm2d(24),

            nn.Upsample(scale_factor=2, mode='bilinear'),
            nn.Conv2d(24, 3, 5, bias=False, padding=2),
            nn.ReLU(),
            nn.BatchNorm2d(3),
            nn.Conv2d(3, 3, 5, padding=2)
        )

    def forward(self, x):
        x = self.encoder(x)
        x = self.decoder(x)
        return x

    def encode_image(self, x):
        x = self.encoder(x)
        x = x.reshape(-1, self.out_dim)

        return x


def preprocess_ae(image):
    image = image.convert('RGB')
    width, height = image.size
    vert_pad = (max(width, height) - height) // 2
    hori_pad = (max(width, height) - width) // 2

    return transforms.Compose([
        transforms.Pad((hori_pad, vert_pad)),
        transforms.Resize((256, 256)),
        transforms.ToTensor(),
    ])(image).reshape(3, 256, 256)
