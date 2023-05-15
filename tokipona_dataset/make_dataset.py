"""
Refernces: https://huggingface.co/datasets/OpenAssistant/oasst1
"""

import torch
import torch.nn.functional as F
from torch.utils.data import Dataset
from torch.utils.data import DataLoader
from datasets import load_dataset
from tokipona_dataset import translator
from models import model
import yaml

with open("models/config/model.yaml") as file:
    config = yaml.safe_load(file)

with open("models/config/tokipona.yaml") as file:
    lang = yaml.safe_load(file)

ds = load_dataset("OpenAssistant/oasst1")
train = ds['train']      # len(train)=84437 (95%)
val = ds['validation']   # len(val)=4401 (5%)


class MakeDataset(Dataset):
    def __init__(self, xs, ys):
        self.xs = xs
        self.ys = ys

    def __len__(self):
        return len(self.xs)
 
    def __getitem__(self, idx):
        x = torch.tensor(self.xs[idx], dtype=torch.float32)
        y = torch.tensor(self.ys[idx], dtype=torch.float32)
        return x, y


def make_datasets(dataset, bulk, stop):
    if stop == -1:
        stop = len(dataset)
    max_length = config["Tokenizer"]["max_length"]
    tokenizer = model.Tokenizer(lang, max_length)
    x_dataset = []
    y_dataset = []

    def sent_to_dataset(sent: torch.Tensor, idx: int) -> tuple[torch.Tensor]:
        x = torch.argmax(sent, dim=-1)
        if x[idx] == tokenizer.dict["[PAD]"]:
            return None, None
        y = x[idx].clone()
        for i in range(x.shape[-1] - idx):
            x[i + idx] = tokenizer.dict["[PAD]"]
        x = F.one_hot(x,num_classes=tokenizer.vocab_size)
        y = F.one_hot(y,num_classes=tokenizer.vocab_size)
        return x, y
    
    for i, data in enumerate(dataset):
        if i >= stop:
            break
        print(f"\rloading: {i+1}/{stop}", end="")
        if data["lang"] == "en":
            sents = translator.translate(data["text"], "English", "toki pona", bulk).split("\n")
            for sent in sents:
                sent = tokenizer.encode(sent, True)
                for  idx in range(max_length - 1):
                    x, y  = sent_to_dataset(sent, idx)
                    if x != None:
                        x_dataset.append(x)
                        y_dataset.append(y)
                        
    print('\r', end="")
    tokipona_dataset = MakeDataset(x_dataset, y_dataset)
    return tokipona_dataset


if __name__ == "__main__":
    train_dataset = make_datasets(train)
    val_dataset = make_datasets(val)
