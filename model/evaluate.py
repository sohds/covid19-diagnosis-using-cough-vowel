import torch
import numpy as np
from sklearn.metrics import roc_curve, auc
from sklearn.preprocessing import label_binarize
import matplotlib.pyplot as plt

def calculate_roc_curve(model, test_loader, num_classes):
    model.eval()
    all_outputs = []
    all_labels = []
    
    with torch.no_grad():
        for images, metadata, labels in test_loader:
            images = images.cuda()
            metadata = metadata.cuda()
            outputs = model(images, metadata=metadata, train=False)
            outputs = torch.softmax(outputs, dim=1)
            
            all_outputs.append(outputs.cpu().numpy())
            all_labels.append(labels.numpy())
    
    all_outputs = np.concatenate(all_outputs)
    all_labels = np.concatenate(all_labels)
    
    # Binarize labels for binary and multi-class cases
    if num_classes == 2:
        all_labels_bin = all_labels
        all_outputs_bin = all_outputs[:, 1]
    else:
        all_labels_bin = label_binarize(all_labels, classes=range(num_classes))
        all_outputs_bin = all_outputs
    
    # Calculate ROC curve and ROC area
    fpr = dict()
    tpr = dict()
    roc_auc = dict()
    
    if num_classes == 2:
        fpr["micro"], tpr["micro"], _ = roc_curve(all_labels_bin, all_outputs_bin)
        roc_auc["micro"] = auc(fpr["micro"], tpr["micro"])
    else:
        for i in range(num_classes):
            fpr[i], tpr[i], _ = roc_curve(all_labels_bin[:, i], all_outputs_bin[:, i])
            roc_auc[i] = auc(fpr[i], tpr[i])
        
        # Compute micro-average ROC curve and ROC area
        fpr["micro"], tpr["micro"], _ = roc_curve(all_labels_bin.ravel(), all_outputs_bin.ravel())
        roc_auc["micro"] = auc(fpr["micro"], tpr["micro"])
    
    return fpr, tpr, roc_auc

def plot_roc_curves(fpr, tpr, roc_auc, title, save_path):
    plt.figure(figsize=(10, 8))
    
    plt.plot(
        fpr["micro"], 
        tpr["micro"],
        label=f'ROC curve (area = {roc_auc["micro"]:.2f})',
        color='deeppink', 
        linestyle=':', 
        linewidth=4
    )
    
    plt.plot([0, 1], [0, 1], 'k--', lw=2)
    plt.xlim([0.0, 1.0])
    plt.ylim([0.0, 1.05])
    plt.xlabel('False Positive Rate')
    plt.ylabel('True Positive Rate')
    plt.title(title)
    plt.legend(loc="lower right")
    
    plt.savefig(save_path)
    plt.close()