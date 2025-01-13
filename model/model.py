import torch
import torch.nn as nn
import torchvision.models as models

class MoCoV2(nn.Module):
    def __init__(self, dim=128, K=4096, m=0.999, T=0.07, num_classes=2):
        super(MoCoV2, self).__init__()
        self.K = K
        self.m = m
        self.T = T
        self.num_classes = num_classes

        # Encoder Q
        self.encoder_q = models.resnet50()
        self.encoder_q.fc = nn.Sequential(
            nn.Linear(self.encoder_q.fc.in_features, 2048),
            nn.ReLU(),
            nn.Linear(2048, dim)
        )

        # Encoder K
        self.encoder_k = models.resnet50()
        self.encoder_k.fc = nn.Sequential(
            nn.Linear(self.encoder_k.fc.in_features, 2048),
            nn.ReLU(),
            nn.Linear(2048, dim)
        )

        # Classifier
        self.classifier = nn.Sequential(
            nn.Linear(dim + 1, 512),  # +1 for metadata
            nn.ReLU(),
            nn.Linear(512, num_classes)
        )

        # Initialize encoder K
        for param_q, param_k in zip(self.encoder_q.parameters(), self.encoder_k.parameters()):
            param_k.data.copy_(param_q.data)
            param_k.requires_grad = False

        # Initialize queue
        self.register_buffer("queue", torch.randn(dim, K))
        self.queue = nn.functional.normalize(self.queue, dim=0)
        self.register_buffer("queue_ptr", torch.zeros(1, dtype=torch.long))
        self.register_buffer("queue_metadata", torch.zeros(K, dtype=torch.long))

    @torch.no_grad()
    def _momentum_update_key_encoder(self):
        for param_q, param_k in zip(self.encoder_q.parameters(), self.encoder_k.parameters()):
            param_k.data = param_k.data * self.m + param_q.data * (1. - self.m)

    @torch.no_grad()
    def _dequeue_and_enqueue(self, keys, metadata):
        batch_size = keys.shape[0]
        ptr = int(self.queue_ptr)

        if ptr + batch_size > self.K:
            batch_size = self.K - ptr
            keys = keys[:batch_size]
            metadata = metadata[:batch_size]

        self.queue[:, ptr:ptr + batch_size] = keys.T
        self.queue_metadata[ptr:ptr + batch_size] = metadata

        ptr = (ptr + batch_size) % self.K
        self.queue_ptr[0] = ptr

    def forward(self, im_q, im_k=None, metadata=None, train=True):
        if train:
            # Compute query features
            q = self.encoder_q(im_q)
            q = nn.functional.normalize(q, dim=1)

            # Compute key features
            with torch.no_grad():
                self._momentum_update_key_encoder()
                k = self.encoder_k(im_k)
                k = nn.functional.normalize(k, dim=1)

            # Contrastive loss computation
            l_pos = torch.einsum('nc,nc->n', [q, k]).unsqueeze(-1)
            l_neg = torch.einsum('nc,ck->nk', [q, self.queue.clone().detach()])
            
            # Combine and apply temperature
            logits = torch.cat([l_pos, l_neg], dim=1)
            logits /= self.T

            # Update queue
            self._dequeue_and_enqueue(k, metadata)
            
            return logits
        else:
            # Feature extraction and classification
            features = self.encoder_q(im_q)
            features = nn.functional.normalize(features, dim=1)
            
            # Combine features with metadata
            combined = torch.cat([features, metadata.unsqueeze(1).float()], dim=1)
            return self.classifier(combined)