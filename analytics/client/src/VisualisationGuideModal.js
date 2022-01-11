import * as React from "react";
import {
  Modal,
  ModalHeader,
  ModalBody,
  ModalFooter,
  ModalButton,
  SIZE,
  ROLE
} from "baseui/modal";
import { KIND as ButtonKind } from "baseui/button";
import { useTranslation } from 'react-i18next';


export default ({visible, dispatch, contents}) => {
  const { t } = useTranslation();
  function closeModal(ev) {
    dispatch({type: 'set', key: 'modalVisible', payload: false});
  }
  if (contents.length === 0) {
    return null;
  }
  const { body, title } = contents[0];
  return (
    <Modal
      onClose={closeModal}
      closeable
      isOpen={visible}
      animate
      autoFocus
      size={SIZE.auto}
      role={ROLE.dialog}
    >
      <ModalHeader>{ title }</ModalHeader>
      <ModalBody dangerouslySetInnerHTML={{__html: body}}>
      </ModalBody>
      <ModalFooter>
        <ModalButton onClick={closeModal}>{t('close')}</ModalButton>
      </ModalFooter>
    </Modal>
  );
}
