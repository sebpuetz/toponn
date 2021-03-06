#!/usr/bin/env python

import tensorflow as tf
from tensorflow.contrib.layers import batch_norm
from enum import Enum
from model import Model


def dropout_wrapper(cell, is_training, keep_prob):
    keep_prob = tf.cond(
        is_training,
        lambda: tf.constant(keep_prob),
        lambda: tf.constant(1.0))
    return tf.contrib.rnn.DropoutWrapper(
        cell, output_keep_prob=keep_prob)


def rnn_layers(
        is_training,
        inputs,
        num_layers=1,
        output_size=50,
        output_dropout=1,
        state_dropout=1,
        seq_lens=None,
        bidirectional=False):
    forward_cell = tf.contrib.rnn.BasicLSTMCell(output_size)
    forward_cell = dropout_wrapper(
        cell=forward_cell,
        is_training=is_training,
        keep_prob=output_dropout)

    if not bidirectional:
        return tf.nn.dynamic_rnn(
            forward_cell,
            inputs,
            dtype=tf.float32,
            sequence_length=seq_lens)

    backward_cell = tf.contrib.rnn.BasicLSTMCell(output_size)
    backward_cell = dropout_wrapper(
        cell=backward_cell,
        is_training=is_training,
        keep_prob=output_dropout)

    return tf.nn.bidirectional_dynamic_rnn(
        forward_cell,
        backward_cell,
        inputs,
        dtype=tf.float32,
        sequence_length=seq_lens)


class RNNModel(Model):
    def __init__(
            self,
            config,
            shapes):
        super(RNNModel, self).__init__(config, shapes)

        self.setup_placeholders()

        inputs = tf.concat([self.tokens, self.tags], axis=2)

        inputs = tf.contrib.layers.dropout(
            inputs,
            keep_prob=config.keep_prob_input,
            is_training=self.is_training)

        (fstates, bstates), _ = rnn_layers(
            self.is_training,
            inputs,
            num_layers=1,
            output_size=config.hidden_size,
            output_dropout=config.keep_prob,
            state_dropout=config.keep_prob,
            seq_lens=self._seq_lens,
            bidirectional=True)
        hidden_states = tf.concat([fstates, bstates], axis=2)

        hidden_states, _ = rnn_layers(self.is_training, hidden_states, num_layers=1, output_size=config.hidden_size,
                                      output_dropout=config.keep_prob,
                                      state_dropout=config.keep_prob, seq_lens=self._seq_lens)

        hidden_states = batch_norm(
            hidden_states,
            decay=0.98,
            scale=True,
            is_training=self.is_training,
            fused=False,
            updates_collections=None)

        topo_logits = tf.layers.dense(hidden_states, shapes['n_labels'], use_bias=True, name="topo_logits")
        if config.crf:
            topo_loss, transitions = self.crf_loss(
                "topo", topo_logits, self.topo_labels)
            topo_predictions = self.crf_predictions(
                "topo", topo_logits, transitions)
        else:
            topo_loss = self.masked_softmax_loss(
                "topo", topo_logits, self.topo_labels, self.mask)
            topo_predictions = self.predictions("topo", topo_logits)

        self.accuracy("topo", topo_predictions, self.topo_labels)

        lr = tf.placeholder(tf.float32, [], "lr")
        self._train_op = tf.train.AdamOptimizer(
            lr).minimize(topo_loss, name="train")
