import os
import librosa
import numpy as np
import torch.utils.data


def random_crop(y, max_length=176400):
    """音声波形を固定長にそろえる

    max_lengthより長かったらランダムに切り取る
    max_lengthより短かったらランダムにパディングする
    """
    if len(y) > max_length:
        max_offset = len(y) - max_length
        offset = np.random.randint(max_offset)
        y = y[offset:max_length + offset]
    else:
        if max_length > len(y):
            max_offset = max_length - len(y)
            offset = np.random.randint(max_offset)
        else:
            offset = 0
        y = np.pad(y, (offset, max_length - len(y) - offset), 'constant')
    return y


class AudioDataset(torch.utils.data.Dataset):

    def __init__(self, df, wav_dir, test=False, sr=None, max_length=4.0, window_size=0.02, hop_size=0.01, n_mels=64):
        if not os.path.exists(wav_dir):
            print('ERROR: not found %s' % wav_dir)
            exit(1)
        self.df = df
        self.wav_dir = wav_dir
        self.test = test
        self.sr = sr
        self.max_length = max_length     # sec
        self.window_size = window_size   # sec
        self.hop_size = hop_size         # sec
        self.n_mels = n_mels

    def __len__(self):
        return len(self.df)

    def __getitem__(self, index):
        fpath = os.path.join(self.wav_dir, self.df.fname[index])
        y, sr = librosa.load(fpath, sr=self.sr)
        if sr is None:
            print('WARNING:', fpath)
            sr = 44100

        y = random_crop(y, int(self.max_length * sr))

        # 特徴抽出
        n_fft = int(self.window_size * sr)
        hop_length = int(self.hop_size * sr)
        mel = librosa.feature.melspectrogram(y=y, sr=sr, n_fft=n_fft, hop_length=hop_length, n_mels=self.n_mels)
        # Conv2Dの場合は (channel, features, frames)
        mel = np.resize(mel, (1, mel.shape[0], mel.shape[1]))
        tensor = torch.from_numpy(mel).float()

        mean = tensor.mean()
        std = tensor.std()
        if std != 0:
            tensor.add_(- mean)
            tensor.div_(std)

        if self.test:
            # テストモードのときは正解ラベルがないのでデータだけ返す
            return tensor
        else:
            # label
            label = self.df.label_idx[index]

            return tensor, label