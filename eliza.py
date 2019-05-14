import logging
import random
import re
import string
from collections import namedtuple
from nltk.tokenize import word_tokenize
import os
from eliza_helpers import ElizaHelpers

import logging
log = logging.getLogger(__name__)
log.level = logging.DEBUG

class KeyBase:
    def __init__(self):
        self.decomps = []


class StoryKey(KeyBase):
    def __init__(self, story_key):
        self.story_key = story_key
        super().__init__()


class Key(KeyBase):
    def __init__(self, word, weight):
        self.word = word
        self.weight = weight
        super().__init__()


class Decomp:
    def __init__(self, parts, save, reasmbs):
        self.parts = parts
        self.save = save
        self.reasmbs = reasmbs
        self.next_reasmb_index = 0
        self.used_indexes = []

    def __repr__(self):
        return str(self.__dict__)


class Reassmebly:
    def __init__(self, parts, goto, story_key):
        self.parts = parts
        self.goto = goto
        self.story_key = story_key

    def __repr__(self):
        return str(self.__dict__)


class Eliza:
    def __init__(self, config_file):
        self.memory = []
        self.load(config_file)
        self.next_story_key = None

    def reinit(self):
        self.initials = []
        self.finals = []
        self.quits = []
        self.pres = {}
        self.posts = {}
        self.synons = {}
        self.keys = {}

    def load(self, path):
        self.reinit()
        key = None
        decomp = None
        with open(path) as file:
            for line in file:
                if not line.strip():
                    continue
                if line[0] == '0':
                    continue
                tag, content = [part.strip() for part in line.split(':')]
                if tag == 'initial':
                    self.initials.append(content)
                elif tag == 'final':
                    self.finals.append(content)
                elif tag == 'quit':
                    self.quits.append(content)
                elif tag == 'pre':
                    parts = content.split(' ')
                    self.pres[parts[0]] = parts[1:]
                elif tag == 'post':
                    parts = content.split(' ')
                    self.posts[parts[0]] = parts[1:]
                elif tag == 'synon':
                    parts = content.split(' ')
                    self.synons[parts[0]] = parts
                elif tag == 'key':
                    parts = content.split(' ')
                    word = parts[0]
                    weight = int(parts[1]) if len(parts) > 1 else 1
                    key = Key(word, weight)
                    self.keys[word] = key
                elif tag == 'story-key':
                    parts = content.split(' ')
                    word = parts[0]
                    key = StoryKey(word)
                    self.keys[word] = key
                    print('story key: %s' % word)
                elif tag == 'decomp':
                    parts = content.split(' ')
                    save = False
                    if parts[0] == '$':
                        save = True
                        parts = parts[1:]
                    decomp = Decomp(parts, save, [])
                    key.decomps.append(decomp)
                elif tag == 'reasmb':
                    parts = content.split(' -> ')
                    word_parts = parts[0].split(' ')

                    story_key  = None
                    if len(parts) > 1:
                        story_key = parts[1]

                    goto = None
                    if word_parts[0] == 'goto':
                        goto = word_parts[1]

                    decomp.reasmbs.append(Reassmebly(
                        parts=word_parts,
                        story_key=story_key,
                        goto=goto))


    def _match_decomp_r(self, parts, words, results):
        if not parts and not words:
            return True
        if not parts or (not words and parts != ['*']):
            return False
        if parts[0] == '*':
            for index in range(len(words), -1, -1):
                results.append(words[:index])
                if self._match_decomp_r(parts[1:], words[index:], results):
                    return True
                results.pop()
            return False
        elif parts[0].startswith('@'):
            root = parts[0][1:]
            if not root in self.synons:
                raise ValueError("Unknown synonym root {}".format(root))
            if not words[0].lower() in self.synons[root]:
                return False
            results.append([words[0]])
            return self._match_decomp_r(parts[1:], words[1:], results)
        elif parts[0].lower() != words[0].lower():
            return False
        else:
            return self._match_decomp_r(parts[1:], words[1:], results)

    def _match_decomp(self, parts, words):
        results = []
        if self._match_decomp_r(parts, words, results):
            return results
        return None

    def _next_reasmb(self, decomp):
        if len(decomp.used_indexes) == len(decomp.reasmbs):
            decomp.used_indexes = []

        possible_indexes = [i for i in range(0, len(decomp.reasmbs)) if i not in decomp.used_indexes]
        index = random.choice(possible_indexes)
        decomp.used_indexes.append(index)
        return decomp.reasmbs[index]

    def _reassemble(self, reasmb, results):
        output = []
        for reword in reasmb:
            if not reword:
                continue
            if reword[0] == '(' and reword[-1] == ')':
                command_parts = reword[1:-1].split(';')
                index = int(command_parts[0])

                if index < 1 or index > len(results):
                    raise ValueError("Invalid result index {}".format(index))

                insert = results[index - 1]

                # would be nice to feed the POS tagger the whole sentence + indexes rather than join and unjoin so much
                for command in command_parts[1:]:
                    print(f'command: {command}')
                    if command == 'gerund':
                        insert = ElizaHelpers.reconjugate_to_gerund(' '.join(insert))

                insert = ElizaHelpers.remove_punctuation(insert)

                output.extend(insert)
            else:
                output.append(reword)

        return output

    def _sub(self, words, sub):
        output = []
        for word in words:
            word_lower = word.lower()
            if word_lower in sub:
                output.extend(sub[word_lower])
            else:
                output.append(word)
        return output

    def _match_key(self, words, key):
        for decomp in key.decomps:
            results = self._match_decomp(decomp.parts, words)
            if results is None:
                log.debug('Decomp did not match: %s', decomp.parts)
                continue
            log.debug('Decomp matched: %s', decomp.parts)
            log.debug('Decomp results: %s', results)
            results = [self._sub(words, self.posts) for words in results]
            log.debug('Decomp results after posts: %s', results)
            reasmb = self._next_reasmb(decomp)
            log.debug('Using reassembly: %s', reasmb)
            if reasmb.goto:
                goto_key = reasmb.goto
                if not goto_key in self.keys:
                    raise ValueError("Invalid goto key {}".format(goto_key))
                log.debug('Goto key: %s', goto_key)
                return self._match_key(words, self.keys[goto_key])
            if reasmb.story_key:
                story_key = reasmb.story_key
                if not story_key in self.keys:
                  raise ValueError("Invalid story key {}".format(story_key))
                log.debug('Storing story key %s for next response' % story_key)
                self.next_story_key = story_key
            output = self._reassemble(reasmb.parts, results)
            if decomp.save:
                self.memory.append(output)
                log.debug('Saved to memory: %s', output)
                continue
            return output
        return None

    def respond(self, text):
        if text in self.quits:
            return None

        words = [w for w in word_tokenize(text) if w and w not in string.punctuation]
        log.debug('Input: %s', words)

        words = self._sub(words, self.pres)
        log.debug('After pre-substitution: %s', words)

        if self.next_story_key:
            keys = [self.keys[self.next_story_key],]
            log.debug('Pulling key from next_story_key: %s', [k.story_key for k in keys])
            print(keys[0].decomps)
            self.next_story_key = None
        else:
            keys = [self.keys[w.lower()] for w in words if w.lower() in self.keys]
            keys = sorted(keys, key=lambda k: -k.weight)
            log.debug('Sorted keys: %s', [(k.word, k.weight) for k in keys])

        output = None

        for key in keys:
            output = self._match_key(words, key)
            if output:
                log.debug('Output from key: %s', output)
                break
        if not output:
            if self.memory:
                index = random.randrange(len(self.memory))
                output = self.memory.pop(index).parts
                log.debug('Output from memory: %s', output)
            else:
                output = self._next_reasmb(self.keys['xnone'].decomps[0]).parts
                log.debug('Output from xnone: %s', output)

        if (len(output) > 1) and (output[-1] in string.punctuation):
            output[-2] += output[-1]
            del output[-1]

        return " ".join(output)

    def initial(self):
        return random.choice(self.initials)

    def final(self):
        return random.choice(self.finals)