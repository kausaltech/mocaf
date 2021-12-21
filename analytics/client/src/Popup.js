import React, { useState } from 'react';

export default function Popup ({state}) {

  return <div style={{
                position: 'fixed',
                top: state.y,
                left: state.x,
                backgroundColor: 'white'
              }}>
           {state.text}
         </div>
}
